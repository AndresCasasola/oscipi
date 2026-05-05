# Oscipi

**Oscipi** es una aplicación diseñada para transformar una Raspberry Pi Pico en un **osciloscopio digital profesional**. Es la herramienta ideal para ingenieros, makers y estudiantes que necesitan visualizar señales eléctricas en tiempo real con una precisión y fluidez que las soluciones básicas no pueden ofrecer.

## ¿Qué es Oscipi?
En esencia, es un sistema de "escucha" de alta velocidad. Mientras que un multímetro te da un número estático (ej. 3.3V), **Oscipi** te permite ver la "película" de esa electricidad: cómo sube, cómo baja, si tiene ruido o si se comporta como debería.

Lo que hace único a Oscipi es su **arquitectura blindada**. Ha sido diseñado para que el hardware trabaje de forma autónoma, asegurando que no se pierda ni un solo detalle de la señal, incluso cuando el ordenador está ocupado procesando los datos.

## ¿Para qué sirve?
*   **Depuración de Circuitos:** Averigua por qué un sensor no funciona o si una señal de comunicación tiene interferencias.
*   **Aprendizaje de Electrónica:** Visualiza ondas senoidales, cuadradas y PWM para entender cómo funciona la teoría en la vida real.
*   **Análisis de Señales:** Mide tiempos exactos, frecuencias y voltajes con una interfaz visual intuitiva en tu ordenador.
*   **Prototipado de Bajo Coste:** Obtén capacidades de visualización profesional usando hardware de apenas 5 euros.

## Características Principales
*   **Visualización Fluida:** Una interfaz en Python optimizada para mostrar miles de datos por segundo sin tirones.
*   **Muestreo Ininterrumpido:** Gracias a su diseño inteligente, el dispositivo nunca "pestañea"; captura la señal de forma continua y sin huecos.
*   **Diseño Robusto:** Inspirado en sistemas críticos, el software detecta automáticamente si hay saturación o errores de datos para avisarte de inmediato.
*   **Modo Simulación:** ¿No tienes la placa a mano? Incluye un generador de señales virtual para que puedas probar la interfaz y tus herramientas de análisis en cualquier lugar.

## Cómo funciona (En un vistazo)
1.  **Captura:** La Raspberry Pi Pico recoge la señal eléctrica a gran velocidad.
2.  **Transporte:** Los datos viajan por USB hacia tu ordenador mediante una "tubería" optimizada.
3.  **Visualización:** La aplicación de escritorio traduce esos números en una gráfica verde brillante, permitiéndote analizar la señal con comodidad.