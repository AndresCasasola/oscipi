#ifndef OSC_COMM_H
#define OSC_COMM_H

#include "FreeRTOS.h"

// FreeRTOS task for USB CDC Communication
void vCommDriverTask(void *pvParameters);

#endif // OSC_COMM_H
