#include "osc_dma.h"
#include "osc_types.h"

#ifndef UNIT_TEST
    #include "pico/stdlib.h"
    #include "hardware/adc.h"
    #include "hardware/dma.h"
    #include "hardware/irq.h"
#else
    // Mocks for unit tests
    #define dma_hw NULL
    #define pdPASS 1
    #define portMAX_DELAY 0xffffffff
    #define pdFALSE 0
    void dma_channel_acknowledge_irq0(int channel) {}
    #define ADC_NUM 0
#endif

// The physical buffer pool
adc_buffer_t buffer_pool[POOL_SIZE];

// The FreeRTOS queues
QueueHandle_t osc_queue_free;
QueueHandle_t osc_queue_ready;

// DMA Channels
static int data_chan;
static int ctrl_chan;

// State variables for the ISR
static adc_buffer_t* current_active_buffer;
static uint32_t global_sequence_counter = 0;
// We need to keep this variable in a known memory location so the Control DMA can read it
static uint32_t next_buffer_address; 

#ifndef UNIT_TEST
// The DMA Interrupt Handler
static void dma_handler() {
    // Clear the interrupt request
    dma_channel_acknowledge_irq0(data_chan);

    // 1. Get the buffer that was just filled
    adc_buffer_t *full_buf = current_active_buffer;

    // 2. Try to pop a new free buffer from the queue for the NEXT cycle
    adc_buffer_t *next_buf = NULL;
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;
    
    if (xQueueReceiveFromISR(osc_queue_free, &next_buf, &xHigherPriorityTaskWoken) == pdPASS) {
        // SUCCESS: We have a replacement. Give it to the control channel for the next chain.
        current_active_buffer = next_buf;
        next_buffer_address = (uint32_t)next_buf->samples;
        
        // 3. Send the full buffer to the PROCESSING task
        full_buf->sequence_id = global_sequence_counter++;
        full_buf->timestamp_us = time_us_32();
        full_buf->flags = 0; // Clear flags
        xQueueSendFromISR(osc_queue_ready, &full_buf, &xHigherPriorityTaskWoken);
        
    } else {
        // CRITICAL ERROR: The free pool is empty (Saturation)
        // We will mark the next buffer (which is whatever we currently have, or dropping data)
        // For safety, we just reuse the full_buf but mark it with an error so the PC knows.
        full_buf->flags |= FLAG_OVERFLOW;
        full_buf->sequence_id = global_sequence_counter++;
        full_buf->timestamp_us = time_us_32();
        
        // We can't really queue it if the processing task is stuck, but we could try or just drop.
        // If we drop, we must keep `next_buffer_address` pointing to full_buf to avoid crashing the DMA.
        next_buffer_address = (uint32_t)full_buf->samples;
        current_active_buffer = full_buf; 
    }

    portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
}

void osc_dma_init(void) {
    // 1. Initialize the FreeRTOS queues
    // The queues store POINTERS to the buffers, not the buffers themselves
    osc_queue_free = xQueueCreate(POOL_SIZE, sizeof(adc_buffer_t*));
    osc_queue_ready = xQueueCreate(POOL_SIZE, sizeof(adc_buffer_t*));

    // Fill the free queue with all available buffers
    for (int i = 0; i < POOL_SIZE; i++) {
        adc_buffer_t* ptr = &buffer_pool[i];
        xQueueSend(osc_queue_free, &ptr, 0);
    }

    // 2. Setup ADC
    adc_init();
    adc_gpio_init(26); // Use GPIO 26 (ADC 0)
    adc_select_input(0);
    
    // Setup ADC FIFO
    adc_fifo_setup(
        true,    // Write each completed conversion to the sample FIFO
        true,    // Enable DMA data request (DREQ)
        1,       // DREQ (and IRQ) asserted when at least 1 sample present
        false,   // We won't see the ERR bit
        false    // Shift each sample to 8 bits when pushing to FIFO (No, keep 12 bits)
    );
    
    // Set ADC sampling rate
    // 48MHz / (clkdiv + 1) = Sample Rate. 
    // Example: For 500kSps, clkdiv = 95.
    adc_set_clkdiv(95); 

    // 3. Setup DMA Channels
    data_chan = dma_claim_unused_channel(true);
    ctrl_chan = dma_claim_unused_channel(true);

    // Setup the Data Channel (The Worker)
    dma_channel_config c_data = dma_channel_get_default_config(data_chan);
    channel_config_set_transfer_data_size(&c_data, DMA_SIZE_16); // 16-bit (ADC provides 12-bit in 16-bit word)
    channel_config_set_read_increment(&c_data, false);           // Read from ADC FIFO (fixed address)
    channel_config_set_write_increment(&c_data, true);           // Increment over the buffer array
    channel_config_set_dreq(&c_data, DREQ_ADC);                  // Pace transfers based on ADC
    channel_config_set_chain_to(&c_data, ctrl_chan);             // Chain to Control Channel when done

    // Setup the Control Channel (The Manager)
    dma_channel_config c_ctrl = dma_channel_get_default_config(ctrl_chan);
    channel_config_set_transfer_data_size(&c_ctrl, DMA_SIZE_32); // Transferring pointers (32-bit addresses)
    channel_config_set_read_increment(&c_ctrl, false);           // Read from our fixed `next_buffer_address` variable
    channel_config_set_write_increment(&c_ctrl, false);          // Write to the Data Channel's WRITE_ADDR register

    // 4. Prime the system for the first run
    adc_buffer_t *first_buf = NULL;
    adc_buffer_t *second_buf = NULL;
    
    xQueueReceive(osc_queue_free, &first_buf, 0);
    xQueueReceive(osc_queue_free, &second_buf, 0);
    
    current_active_buffer = first_buf;
    next_buffer_address = (uint32_t)second_buf->samples;

    // Apply configuration to Data Channel (but don't start yet)
    dma_channel_configure(
        data_chan,
        &c_data,
        first_buf->samples,  // Initial write address
        &adc_hw->fifo,       // Initial read address
        SAMPLES_PER_BUFFER,  // Number of transfers
        false                // Don't start yet
    );

    // Apply configuration to Control Channel
    dma_channel_configure(
        ctrl_chan,
        &c_ctrl,
        &dma_hw->ch[data_chan].al1_write_addr, // Write to the Data Channel's write address register
        &next_buffer_address,                  // Read from our state variable
        1,                                     // Only one transfer (one address)
        false                                  // Don't start yet
    );

    // 5. Setup DMA Interrupts
    dma_channel_set_irq0_enabled(data_chan, true);
    irq_set_exclusive_handler(DMA_IRQ_0, dma_handler);
    irq_set_enabled(DMA_IRQ_0, true);

    // 6. Start the engines!
    dma_start_channel_mask((1u << data_chan)); // Start the data channel
    adc_run(true);                             // Start the ADC
}
#else
// Mock for unit tests
void osc_dma_init(void) {
    // Empty
}
#endif
