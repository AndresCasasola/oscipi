#include <stdio.h>
#include "pico/stdlib.h"
#include "FreeRTOS.h"
#include "task.h"

// Definimos el pin del LED para la Pico estándar
const uint LED_PIN = PICO_DEFAULT_LED_PIN; // Normalmente el pin 25

/**
 * Tarea de parpadeo (Blink Task)
 * En FreeRTOS, las tareas son bucles infinitos que nunca deben retornar.
 */
void vBlinkTask(void *pvParameters) {
    // Inicializamos el GPIO del LED
    gpio_init(LED_PIN);
    gpio_set_dir(LED_PIN, GPIO_OUT);

    while (true) {
        gpio_put(LED_PIN, 1);
        // Usamos vTaskDelay en lugar de sleep_ms. 
        // Esto libera el procesador para que otras tareas trabajen.
        vTaskDelay(pdMS_TO_TICKS(300)); 

        gpio_put(LED_PIN, 0);
        vTaskDelay(pdMS_TO_TICKS(300));
    }
}

int main() {
    // Inicializa USB/UART para poder usar printf en el futuro
    stdio_init_all();

    // Creamos la tarea
    // 1. Puntero a la función de la tarea
    // 2. Nombre descriptivo (para debugging)
    // 3. Tamaño del Stack (en palabras, no bytes)
    // 4. Parámetros de entrada (ninguno en este caso)
    // 5. Prioridad (1 es baja, cuanto más alta el número, más prioridad)
    // 6. Handler de la tarea (no lo necesitamos ahora)
    xTaskCreate(vBlinkTask, "Blink_Task", 256, NULL, 1, NULL);

    // Arrancamos el Scheduler (el corazón de FreeRTOS)
    // A partir de aquí, FreeRTOS toma el control total del procesador
    vTaskStartScheduler();

    // El código nunca debería llegar aquí
    while (true) {
        tight_loop_contents();
    }
}