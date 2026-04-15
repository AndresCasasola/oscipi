#include "unity.h"
#include <stdbool.h>

// --- Stubs Implementation ---
void stdio_init_all(void) {}
void vTaskStartScheduler(void) {}
void xTaskCreate(void* f, const char* name, int stack, void* param, int prio, void* handle) {}
void vTaskDelay(int x) {}

bool last_led_state = false;
int gpio_init_called_count = 0;
int gpio_set_dir_called_count = 0;

void gpio_init(unsigned int pin) { (void)pin; gpio_init_called_count++; }
void gpio_set_dir(unsigned int pin, unsigned int dir) { (void)pin; (void)dir; gpio_set_dir_called_count++; }
void gpio_put(unsigned int pin, bool value) { (void)pin; last_led_state = value; }

// --- External logic from main.c ---
extern void led_init(void);
extern void led_set_state(bool led_on);

void setUp(void) {
    last_led_state = false;
    gpio_init_called_count = 0;
    gpio_set_dir_called_count = 0;
}
void tearDown(void) {}

void test_led_init_should_setup_gpio(void) {
    led_init();
    TEST_ASSERT_EQUAL_INT(1, gpio_init_called_count);
}

void test_led_set_state_should_change_hardware_output(void) {
    led_set_state(true);
    TEST_ASSERT_TRUE(last_led_state);
    led_set_state(false);
    TEST_ASSERT_FALSE(last_led_state);
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_led_init_should_setup_gpio);
    RUN_TEST(test_led_set_state_should_change_hardware_output);
    return UNITY_END();
}