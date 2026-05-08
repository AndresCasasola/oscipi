#include <pico/time.h>
#include <stdio.h> // IWYU pragma: keep
#include <math.h>

#include "pico/stdlib.h" // IWYU pragma: keep
#include "pico/stdio_usb.h"

#include "hardware/adc.h" // IWYU pragma: keep
#include "hardware/dma.h" // IWYU pragma: keep
#include "hardware/irq.h" // IWYU pragma: keep

#include "oscipi_types.h"

void oscipi_led_init(void) {
    gpio_init(PICO_DEFAULT_LED_PIN);
    gpio_set_dir(PICO_DEFAULT_LED_PIN, GPIO_OUT);
}

void oscipi_led_set(bool led_on) {
    gpio_put(PICO_DEFAULT_LED_PIN, led_on);
}

static bool oscipi_led_timer_callback(repeating_timer_t *rt) {
    static bool led_state = false;
    led_state = !led_state;
    oscipi_led_set(led_state);
    return true; // Keep repeating
}

static uint16_t oscipi_calculate_checksum(adc_buffer_t *buf) {
    uint16_t checksum = 0;
    
    // Checksum over metadata (sequence_id + timestamp_us = 8 bytes = 4 uint16_t)
    uint16_t *meta_ptr = (uint16_t*)&buf->sequence_id;
    for(int i=0; i < 4; i++) {
        checksum ^= meta_ptr[i];
    }
    
    // Checksum over flags (with 0x00 padding)
    checksum ^= (uint16_t)buf->flags;

    // Checksum over samples
    for (int i = 0; i < SAMPLES_PER_BUFFER; i++) {
        checksum ^= buf->samples[i];
    }
    
    return checksum;
}

// Sine table aligned for optional ring buffer usage in the future
uint16_t raw_sin[SAMPLES_PER_BUFFER] __attribute__((aligned(2048)));

// Pointer to reset the read address via control channel
uint32_t reset_read_addr = (uint32_t)raw_sin;

int main() {
    stdio_init_all();
    // Disable \n translation to \r\n for binary data over USB CDC
    stdio_set_translate_crlf(&stdio_usb, false);

    // Set blinky led: Just a fast "running" debug.
    oscipi_led_init();
    static repeating_timer_t led_timer;
    add_repeating_timer_ms(500, oscipi_led_timer_callback, NULL, &led_timer);

    // Build sine table
    int i;
    for (i=0; i<(SAMPLES_PER_BUFFER); i++){
        raw_sin[i] = (uint16_t)(2047 * sin((float)i*6.283/(float)SAMPLES_PER_BUFFER) + 2047); //12 bit
    }

    adc_buffer_t buf;
    uint32_t counter = 0;
    const uint8_t header[2] = {0xAA, 0x55};

    // ------------------------------------------------------------------------
    // v0.2: DMA CONFIGURATION
    // ------------------------------------------------------------------------

    // Claim a DMA timer to pace the data generation
    // System clock is 125 MHz. We want approx 500 kHz sampling.
    // 125,000,000 / 500,000 = 250. So fraction is 1/250.
    int dma_timer = dma_claim_unused_timer(true);
    dma_timer_set_fraction(dma_timer, 1, 250);
    uint timer_dreq = dma_get_timer_dreq(dma_timer);

    int chan_data = dma_claim_unused_channel(true);
    int chan_ctrl = dma_claim_unused_channel(true);

    // --- Control Channel Setup ---
    // The control channel resets the Data channel's read_addr.
    dma_channel_config cfg_ctrl = dma_channel_get_default_config(chan_ctrl);
    channel_config_set_transfer_data_size(&cfg_ctrl, DMA_SIZE_32);
    channel_config_set_read_increment(&cfg_ctrl, false);
    channel_config_set_write_increment(&cfg_ctrl, false);

    dma_channel_configure(
        chan_ctrl,
        &cfg_ctrl,
        &dma_hw->ch[chan_data].read_addr,          
        &reset_read_addr,                          // Read from our fixed pointer
        1,                                         // 1 transfer
        false                                      // Do not start yet
    );

    // --- Data Channel Setup ---
    // The data channel copies from raw_sin to buf.samples
    dma_channel_config cfg_data = dma_channel_get_default_config(chan_data);
    channel_config_set_transfer_data_size(&cfg_data, DMA_SIZE_16);
    channel_config_set_read_increment(&cfg_data, true);
    channel_config_set_write_increment(&cfg_data, true);
    channel_config_set_dreq(&cfg_data, timer_dreq);
    channel_config_set_chain_to(&cfg_data, chan_ctrl);

    dma_channel_configure(
        chan_data,
        &cfg_data,
        buf.samples,         // Write to output buffer
        raw_sin,             // Read from sine table
        SAMPLES_PER_BUFFER,  // Transfer 1024 samples
        false                // Do not start yet
    );

    // Start the first transfer
    dma_channel_start(chan_data);

    // ------------------------------------------------------------------------
    // MAIN CPU LOOP
    // ------------------------------------------------------------------------
    while (true) {
        // Wait for the DMA data channel to finish the current frame
        dma_channel_wait_for_finish_blocking(chan_data);

        // 1. Fill Metadata
        buf.sequence_id = counter++;
        buf.timestamp_us = time_us_32();
        buf.flags = 0;

        // 2. Calculate Checksum
        uint16_t checksum = oscipi_calculate_checksum(&buf);

        // 3. Send Frame over USB CDC
        fwrite(header, 1, 2, stdout);
        fwrite(&buf.sequence_id, 1, 4, stdout);
        fwrite(&buf.timestamp_us, 1, 4, stdout);
        
        uint8_t flags_pad[2] = {buf.flags, 0x00};
        fwrite(flags_pad, 1, 2, stdout);
        
        fwrite(buf.samples, 1, SAMPLES_PER_BUFFER * 2, stdout);
        fwrite(&checksum, 1, 2, stdout);
        
        fflush(stdout);

        // Reset the write address for the data channel (since buf is fixed but write_addr increments)
        dma_hw->ch[chan_data].write_addr = (uint32_t)buf.samples;
        
        // Reset the control channel's transfer count so it's ready for the next chain
        // We trigger the Data channel by starting the Data channel directly,
        // or by starting the Control channel. Let's just start the Data channel.
        dma_hw->ch[chan_ctrl].transfer_count = 1;
        dma_channel_start(chan_data);
    }
}
