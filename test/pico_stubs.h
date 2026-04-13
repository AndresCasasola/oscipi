#ifndef PICO_STUBS_H
#define PICO_STUBS_H

#include <stdbool.h>

#define PICO_OK 0
#define PICO_DEFAULT_LED_PIN 25

// Variables globales para que el test "vea" qué hizo el código
extern bool last_led_state;
extern int gpio_init_called_count;

// Simulamos las funciones del SDK
void gpio_init(int pin);
void gpio_set_dir(int pin, int dir);
void gpio_put(int pin, bool value);
void hard_assert(bool condition);
#define GPIO_OUT 1

#endif