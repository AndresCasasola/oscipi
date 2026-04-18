#ifndef OSC_TYPES_H
#define OSC_TYPES_H

#include <stdint.h>
#include <stdbool.h>

#define SAMPLES_PER_BUFFER 1024
#define POOL_SIZE 8

// Error flags
#define FLAG_OVERFLOW 0x01
#define FLAG_GAP_DETECTED 0x02

typedef struct {
    // Metadata for traceability
    uint32_t sequence_id;     // Incremental counter
    uint32_t timestamp_us;    // Timestamp in microseconds
    // System state
    uint8_t  flags;           // Bitmask of flags
    // ADC Data (12-bit, stored in uint16_t)
    uint16_t samples[SAMPLES_PER_BUFFER];
} adc_buffer_t;

#endif // OSC_TYPES_H
