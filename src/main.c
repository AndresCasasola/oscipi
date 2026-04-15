#include <stdio.h>

#ifndef UNIT_TEST
    #include "pico/stdlib.h"
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
        vTaskDelay(pdMS_TO_TICKS(300)); 

        led_set_state(false);
        vTaskDelay(pdMS_TO_TICKS(300));
    }
}

// --- Application Entry Point ---
#ifndef UNIT_TEST
int main() {
    stdio_init_all();
    xTaskCreate(vBlinkTask, "Blink_Task", 256, NULL, 1, NULL);
    vTaskStartScheduler();
    while (true) {
        tight_loop_contents();
    }
}
#endif