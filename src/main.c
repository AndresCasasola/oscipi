#include <stdio.h>
#include "pico/stdlib.h"
#include "hardware/adc.h"
#include "osc_types.h"

// Re-implement the checksum logic here so we don't need to call the comm task
static uint16_t calculate_checksum(adc_buffer_t *buf) {
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

int main() {
    stdio_init_all();
    
    // Disable \n translation to \r\n for binary data over USB CDC
    stdio_set_translate_crlf(&stdio_usb, false);

    // Initialize ADC hardware
    adc_init();
    
    // Make sure GPIO 26 is high-impedance, no pullups etc
    adc_gpio_init(26);
    
    // Select ADC input 0 (GPIO 26)
    adc_select_input(0);

    adc_buffer_t buf;
    uint32_t counter = 0;
    const uint8_t header[2] = {0xAA, 0x55};

    while (1) {
        // 1. Fill Metadata
        buf.sequence_id = counter++;
        buf.timestamp_us = time_us_32();
        buf.flags = 0;

        // 2. Slow Polling ADC Read
        for (int i = 0; i < SAMPLES_PER_BUFFER; i++) {
            buf.samples[i] = adc_read();
            
            // Sleep 1ms between samples -> 1000 samples per second
            // This means one 1024-sample frame takes about ~1.02 seconds to fill
            sleep_us(1000); 
        }

        // 3. Calculate Checksum
        uint16_t checksum = calculate_checksum(&buf);

        // 4. Send Frame over USB CDC
        fwrite(header, 1, 2, stdout);
        fwrite(&buf.sequence_id, 1, 4, stdout);
        fwrite(&buf.timestamp_us, 1, 4, stdout);
        
        uint8_t flags_pad[2] = {buf.flags, 0x00};
        fwrite(flags_pad, 1, 2, stdout);
        
        fwrite(buf.samples, 1, SAMPLES_PER_BUFFER * 2, stdout);
        fwrite(&checksum, 1, 2, stdout);
        
        // Push the data out
        fflush(stdout);
    }
}