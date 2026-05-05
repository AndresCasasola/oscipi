# ROADMAP

## 1. Done


## 2. To Do
- [ ] Implementar la recogida de datos con DMA.
- [ ] Mejorar la interfaz del osciloscopio en QT.
- [ ] Implementar un protocolo de comunicación entre la interfaz QT y el MCU. La interfaz en QT ejecuta funciones que pueden afectar a la propia UI y también pueden enviar comandos al MCU. Por ejemplo, cambiar la frecuencia de muestreo. Para ello diseñaremos un protocolo que enviará un paquete de datos desde QT al MCU. En él habrá de indicarse el comando, los parámetros que acompañan al comando y un CRC para comprobar que el paquete se ha recibido correctamente. En el MCU habrá una especie de tabla de punteros a funciones y con un enum cada comando recibido ejecutará su correspondiente función.