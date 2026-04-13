#include "unity.h"
#include "pico_stubs.h"

// Variables para trackear el hardware simulado
bool last_led_state = false;
int gpio_init_called_count = 0;

// Implementación de los "Mocks" (Stubs)
void gpio_init(int pin) { (void)pin; gpio_init_called_count++; }
void gpio_set_dir(int pin, int dir) { (void)pin; (void)dir; }
void gpio_put(int pin, bool value) { last_led_state = value; }

// Corregimos el assert para Unity
void hard_assert(bool condition) { 
    if(!condition) {
        UNITY_TEST_FAIL(__LINE__, "Hard Assert Failed!"); 
    }
}

// Prototipos de las funciones que estamos testeando
extern int pico_led_init(void);
extern void pico_set_led(bool led_on);

void setUp(void) {
    last_led_state = false;
    gpio_init_called_count = 0;
}

void tearDown(void) {}

void test_pico_led_init_debe_llamar_a_gpio_init(void) {
    int rc = pico_led_init();
    TEST_ASSERT_EQUAL_INT(PICO_OK, rc);
    TEST_ASSERT_EQUAL_INT(1, gpio_init_called_count);
}

void test_pico_set_led_cambia_el_estado_correctamente(void) {
    pico_set_led(true);
    TEST_ASSERT_TRUE(last_led_state);
    
    pico_set_led(false);
    TEST_ASSERT_FALSE(last_led_state);
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_pico_led_init_debe_llamar_a_gpio_init);
    RUN_TEST(test_pico_set_led_cambia_el_estado_correctamente);
    return UNITY_END();
}