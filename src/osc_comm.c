#include "osc_comm.h"
#include "osc_processing.h"
#include "osc_dma.h"
#include "osc_types.h"
#include <stdio.h>

#ifndef UNIT_TEST
    #include "pico/stdlib.h"
#else
    #define pdPASS 1
    #define portMAX_DELAY 0xffffffff
#endif

// Simple XOR checksum for speed
static uint16_t calculate_checksum(adc_buffer_t *buf) {
    uint16_t checksum = 0;
    
    // Checksum over metadata
    uint16_t *meta_ptr = (uint16_t*)&buf->sequence_id;
    for(int i=0; i < 4; i++) { // 8 bytes = 4 uint16_t
        checksum ^= meta_ptr[i];
    }
    
    checksum ^= (uint16_t)buf->flags;

    // Checksum over samples
    for (int i = 0; i < SAMPLES_PER_BUFFER; i++) {
        checksum ^= buf->samples[i];
    }
    
    return checksum;
}

void vCommDriverTask(void *pvParameters) {
    adc_buffer_t *buffer_to_send = NULL;
    const uint8_t header[2] = {0xAA, 0x55};

    while (1) {
        // Wait for a processed buffer
        if (xQueueReceive(osc_queue_ready_to_send, &buffer_to_send, portMAX_DELAY) == pdPASS) {
            
            // 1. Send Header
            fwrite(header, 1, 2, stdout);
            
            // 2. Send Metadata
            fwrite(&buffer_to_send->sequence_id, 1, 4, stdout);
            fwrite(&buffer_to_send->timestamp_us, 1, 4, stdout);
            
            // Send Flags + 1 byte padding to keep alignment
            uint8_t flags_pad[2] = {buffer_to_send->flags, 0x00};
            fwrite(flags_pad, 1, 2, stdout);
            
            // 3. Send Payload (Samples)
            fwrite(buffer_to_send->samples, 1, SAMPLES_PER_BUFFER * 2, stdout);
            
            // 4. Send Checksum
            uint16_t checksum = calculate_checksum(buffer_to_send);
            fwrite(&checksum, 1, 2, stdout);
            
            // Flush to ensure data is pushed via USB CDC
            fflush(stdout);

            // 5. IMPORTANT: Return the buffer to the free pool
            xQueueSend(osc_queue_free, &buffer_to_send, 0);
        }
    }
}
