#include <pico/time.h>
#include <stdio.h> // IWYU pragma: keep
#include <math.h>

#include "pico/stdlib.h" // IWYU pragma: keep
#include "pico/stdio_usb.h"

#include "hardware/adc.h" // IWYU pragma: keep
#include "hardware/dma.h" // IWYU pragma: keep
#include "hardware/irq.h" // IWYU pragma: keep

#include "osc_types.h"

// A-channel, 1x, active
#define DAC_config_chan_A 0b0011000000000000

// Sine table
uint16_t raw_sin[SAMPLES_PER_BUFFER];
// Table of values to be sent to DAC
//unsigned short DAC_data[SAMPLES_PER_BUFFER];
// Pointer to the address of the DAC data table
//unsigned short * address_pointer = &DAC_data[0];
// Number of DMA transfers per event
//const uint32_t transfer_count = SAMPLES_PER_BUFFER;

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

    // Build sine table and DAC data table
    int i;
    for (i=0; i<(SAMPLES_PER_BUFFER); i++){
        raw_sin[i] = (uint16_t)(2047 * sin((float)i*6.283/(float)SAMPLES_PER_BUFFER) + 2047); //12 bit
        //DAC_data[i] = DAC_config_chan_A | (raw_sin[i] & 0x0fff);
    }

    adc_buffer_t buf;
    uint32_t counter = 0;
    const uint8_t header[2] = {0xAA, 0x55};

    while (true) {
        // 1. Fill Metadata
        buf.sequence_id = counter++;
        buf.timestamp_us = time_us_32();
        buf.flags = 0;

        // 2. Fill buffer to send
        for (int i = 0; i < SAMPLES_PER_BUFFER; i++) {
            buf.samples[i] = raw_sin[i];

            sleep_us(750);
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
