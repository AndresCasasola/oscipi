#include <stdio.h>
#include "osc_types.h"
#include "osc_dma.h"
#include "osc_processing.h"
#include "osc_comm.h"

#ifndef UNIT_TEST
    #include "pico/stdlib.h"
    #include "pico/stdio_usb.h"
    #include "FreeRTOS.h"
    #include "task.h"
#else
    #include <stdbool.h>
    typedef unsigned int uint;
    #define GPIO_OUT 1
    #define pdMS_TO_TICKS(x) x
    #define tight_loop_contents() 
    
    // Prototypes for stubs
    void gpio_init(uint pin);
    void gpio_set_dir(uint pin, uint dir);
    void gpio_put(uint pin, bool value);
    void vTaskDelay(int x);
    void stdio_init_all(void);
    void xTaskCreate(void* f, const char* name, int stack, void* param, int prio, void* handle);
    void vTaskStartScheduler(void);
#endif

#ifndef PICO_DEFAULT_LED_PIN
    #define PICO_DEFAULT_LED_PIN 25
#endif

const uint LED_PIN = PICO_DEFAULT_LED_PIN;

// --- Helper functions for testability ---
void led_init(void) {
    gpio_init(LED_PIN);
    gpio_set_dir(LED_PIN, GPIO_OUT);
}

void led_set_state(bool led_on) {
    gpio_put(LED_PIN, led_on);
}

// --- Tasks ---
void vBlinkTask(void *pvParameters) {
    led_init();

    while (true) {
        led_set_state(true);
        vTaskDelay(pdMS_TO_TICKS(500)); 

        led_set_state(false);
        vTaskDelay(pdMS_TO_TICKS(500));
    }
}

// Mock Task to generate fake data and push it to the Processing Task
void vMockDMATask(void *pvParameters) {
    adc_buffer_t *current_buffer = NULL;
    uint32_t counter = 0;
    
    while(1) {
        // Wait for a free buffer
        if (xQueueReceive(osc_queue_free, &current_buffer, portMAX_DELAY) == pdPASS) {
            
            // Fill Metadata
            current_buffer->sequence_id = counter++;
            current_buffer->timestamp_us = time_us_32();
            current_buffer->flags = 0;
            
            // Generate a simple Sawtooth Wave for visual testing
            for(int i = 0; i < SAMPLES_PER_BUFFER; i++) {
                current_buffer->samples[i] = (i * 4) % 4096;
            }
            
            // Send to Processing Task
            xQueueSend(osc_queue_ready, &current_buffer, 0);
            
            // Delay 20ms (simulate 50 FPS)
            vTaskDelay(pdMS_TO_TICKS(20));
        }
    }
}

// --- Application Entry Point ---
#ifndef UNIT_TEST
int main() {
    stdio_init_all();
    
    // Disable \n translation to \r\n for binary data over USB CDC
    stdio_set_translate_crlf(&stdio_usb, false);

    // Initialize Architecture Components
    osc_dma_init();        // Will initialize queues, but hardware is disabled in osc_dma.c
    osc_processing_init(); // Will initialize processing queue

    // Create FreeRTOS Tasks
    xTaskCreate(vMockDMATask, "Mock_Task", 1024, NULL, 4, NULL);
    xTaskCreate(vDataProcessingTask, "Process_Task", 1024, NULL, 3, NULL);
    xTaskCreate(vCommDriverTask, "Comm_Task", 1024, NULL, 2, NULL);
    xTaskCreate(vBlinkTask, "Blink_Task", 256, NULL, 1, NULL);
    
    vTaskStartScheduler();
    while (true) {
        tight_loop_contents();
    }
}
#endif