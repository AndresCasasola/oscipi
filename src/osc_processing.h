#ifndef OSC_PROCESSING_H
#define OSC_PROCESSING_H

#include "FreeRTOS.h"
#include "queue.h"

// Queue to pass processed buffers to the communication task
extern QueueHandle_t osc_queue_ready_to_send;

// Initialize processing resources (e.g., queues)
void osc_processing_init(void);

// FreeRTOS task for data processing
void vDataProcessingTask(void *pvParameters);

#endif // OSC_PROCESSING_H
