#ifndef UNIT_TESTING
    #include "pico/stdlib.h"
#else
    // Si estamos testeando, incluimos nuestros "engaños" (stubs)
    #include "pico_stubs.h"
#endif

#ifndef LED_DELAY_MS
#define LED_DELAY_MS 1000
#endif

int pico_led_init(void) {
#if defined(PICO_DEFAULT_LED_PIN)
    gpio_init(PICO_DEFAULT_LED_PIN);
    gpio_set_dir(PICO_DEFAULT_LED_PIN, GPIO_OUT);
    return PICO_OK;
#else
    return -1;
#endif
}

void pico_set_led(bool led_on) {
#if defined(PICO_DEFAULT_LED_PIN)
    gpio_put(PICO_DEFAULT_LED_PIN, led_on);
#endif
}

#ifndef UNIT_TESTING
int main() {
    int rc = pico_led_init();
    hard_assert(rc == PICO_OK);
    while (true) {
        pico_set_led(true);
        sleep_ms(LED_DELAY_MS);
        pico_set_led(false);
        sleep_ms(LED_DELAY_MS);
    }
    return 0;
}
#endif