#ifndef OSCIPI_TYPES_H
#define OSCIPI_TYPES_H

#include <stdint.h>
#include <stdbool.h>

#define SAMPLES_PER_BUFFER 1024

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

/* * Telemetry structure following the Open/Closed principle.
 * We extend the functionality by wrapping the original buffer 
 * instead of modifying it.
 */
typedef struct {
    // Performance Telemetry (16 bytes)
    uint32_t dma_us;           // Time taken by hardware DMA transfer
    uint32_t metadata_us;      // Time spent filling headers/timestamps
    uint32_t checksum_us;      // Time spent calculating XOR checksum
    uint32_t usb_transport_us; // Blocking time during USB transmission
    uint32_t total_loop_us;    // Total cycle time
    
    // Original Data Structure
    adc_buffer_t adc_buf; 
} telemetry_frame_t;

#endif // OSCIPI_TYPES_H
