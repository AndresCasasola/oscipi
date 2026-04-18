#include "osc_processing.h"
#include "osc_dma.h"
#include "osc_types.h"

#ifndef UNIT_TEST
    #include "pico/stdlib.h"
#else
    #define pdPASS 1
    #define portMAX_DELAY 0xffffffff
#endif

QueueHandle_t osc_queue_ready_to_send;

void osc_processing_init(void) {
    // Create the queue to pass data to the UART/USB task
    osc_queue_ready_to_send = xQueueCreate(POOL_SIZE, sizeof(adc_buffer_t*));
}

void vDataProcessingTask(void *pvParameters) {
    adc_buffer_t *current_buffer = NULL;
    uint32_t last_sequence_id = 0;
    bool first_run = true;

    while (1) {
        // 1. Wait for DMA/ISR to send us a full buffer
        if (xQueueReceive(osc_queue_ready, &current_buffer, portMAX_DELAY) == pdPASS) {
            
            // 2. Integrity Validation
            if (!first_run) {
                if (current_buffer->sequence_id != last_sequence_id + 1) {
                    // GAP DETECTED! We lost a buffer.
                    current_buffer->flags |= FLAG_GAP_DETECTED;
                }
            }
            
            // 3. Data Processing (Placeholder for future digital filtering, trigger, etc.)
            // For now, we just pass the raw data through.
            
            // 4. Update state
            last_sequence_id = current_buffer->sequence_id;
            first_run = false;
            
            // 5. Send the buffer to the communication task
            // If the comm task is too slow, this could fail. 
            // In a robust system, we might handle this gracefully (e.g., drop the frame and recycle).
            if (xQueueSend(osc_queue_ready_to_send, &current_buffer, 0) != pdPASS) {
                // The comm task queue is full! The PC is not reading fast enough.
                // We must return the buffer to the free pool immediately so the DMA doesn't starve.
                xQueueSend(osc_queue_free, &current_buffer, 0);
            }
        }
    }
}
