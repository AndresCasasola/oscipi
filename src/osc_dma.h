#ifndef OSC_DMA_H
#define OSC_DMA_H

#include "FreeRTOS.h"
#include "queue.h"

// Expose the FreeRTOS queues for other tasks to use
extern QueueHandle_t osc_queue_free;
extern QueueHandle_t osc_queue_ready;

// Initialize the ADC, DMA, and the FreeRTOS buffer queues
void osc_dma_init(void);

#endif // OSC_DMA_H
