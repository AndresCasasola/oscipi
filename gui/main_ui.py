import sys
import time
import struct
import numpy as np
import serial
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg

# --- CONFIGURACIÓN GLOBAL DEL BÚNKER ---
SIMULATE_MODE = True  # Cambia a False para conectar con la Pico real
SERIAL_PORT = "COM3"   # Ajusta según tu sistema (ej: /dev/ttyACM0 en Linux)
BAUDRATE = 921600
SAMPLES_PER_BUFFER = 1024
DISPLAY_CHUNKS = 5     # Cuántos buffers queremos ver en pantalla a la vez
ADC_MAX_VAL = 4095     # Resolución de 12 bits de la Pico

# --- CAPA DE DATOS (MODULARIZADA) ---

class DataSource(QtCore.QThread):
    """Interfaz base para fuentes de datos"""
    new_data_signal = QtCore.pyqtSignal(np.ndarray)
    
    def __init__(self):
        super().__init__()
        self.running = True

    def stop(self):
        self.running = False

class MockPicoSource(DataSource):
    """Simulador: Genera una onda seno con ruido para pruebas sin hardware"""
    def run(self):
        phase = 0.0
        while self.running:
            # Generar tiempo y onda
            t = np.linspace(phase, phase + 2*np.pi, SAMPLES_PER_BUFFER)
            
            # 2048 es el centro del ADC (3.3V / 2), 1500 la amplitud
            noise = np.random.normal(0, 15, SAMPLES_PER_BUFFER)
            samples = (2048 + 1500 * np.sin(t) + noise).astype(np.uint16)
            
            # Limitar para que no se salga del rango ADC
            samples = np.clip(samples, 0, ADC_MAX_VAL)
            
            self.new_data_signal.emit(samples)
            
            phase += 0.1 # Velocidad de movimiento de la onda
            time.sleep(0.02) # ~50 FPS para suavidad total

class SerialPicoSource(DataSource):
    """Driver Real: Lee el protocolo de tramas definido para el búnker"""
    def run(self):
        try:
            with serial.Serial(self.port, BAUDRATE, timeout=1) as ser:
                while self.running:
                    # Buscar cabecera de sincronización 0xAA 0x55
                    if ser.read(1) == b'\xaa':
                        if ser.read(1) == b'\x55':
                            # Leer metadatos: ID (4 bytes) + Timestamp (4 bytes)
                            _ = ser.read(8) 
                            
                            # Leer 1024 muestras (2 bytes cada una)
                            raw_payload = ser.read(SAMPLES_PER_BUFFER * 2)
                            
                            if len(raw_payload) == SAMPLES_PER_BUFFER * 2:
                                # Conversión ultra rápida de bytes a NumPy
                                samples = np.frombuffer(raw_payload, dtype='<H')
                                self.new_data_signal.emit(samples)
        except Exception as e:
            print(f"ERROR CRÍTICO UART: {e}")

# --- CAPA DE INTERFAZ GRÁFICA (PYQTGRAPH) ---

class OscilloscopeUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # 1. Configuración de la Ventana
        self.setWindowTitle("Pico-OS | Professional Real-Time Oscilloscope")
        self.resize(1100, 700)
        self.setStyleSheet("background-color: #121212; color: #E0E0E0;")

        # 2. Layout Principal
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QtWidgets.QVBoxLayout(self.central_widget)

        # 3. Widget de Gráfica
        self.plot_widget = pg.PlotWidget(title="ADC Signal Stream")
        self.plot_widget.setYRange(0, ADC_MAX_VAL)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)
        self.plot_widget.getAxis('left').setLabel('Amplitude', units='ADC Units')
        self.plot_widget.getAxis('bottom').setLabel('Samples')
        
        # Estilo de la curva (Verde fosforito clásico de osciloscopio)
        self.curve = self.plot_widget.plot(pen=pg.mkPen(color='#39FF14', width=1.5))
        self.main_layout.addWidget(self.plot_widget)

        # 4. Buffer de Visualización (Efecto de persistencia)
        self.display_buffer = np.full(SAMPLES_PER_BUFFER * DISPLAY_CHUNKS, 2048)

        # 5. Inicialización de Fuente de Datos
        if SIMULATE_MODE:
            self.data_source = MockPicoSource()
            self.statusBar().showMessage("MODO SIMULACIÓN ACTIVO (Sin Hardware)")
        else:
            self.data_source = SerialPicoSource()
            self.data_source.port = SERIAL_PORT
            self.statusBar().showMessage(f"CONECTADO A: {SERIAL_PORT}")

        # Conectar señal y arrancar
        self.data_source.new_data_signal.connect(self.update_plot)
        self.data_source.start()

    def update_plot(self, new_samples):
        """Actualiza la gráfica con el nuevo bloque de datos"""
        # Desplazar el buffer a la izquierda y meter los nuevos datos al final
        self.display_buffer = np.roll(self.display_buffer, -SAMPLES_PER_BUFFER)
        self.display_buffer[-SAMPLES_PER_BUFFER:] = new_samples
        
        # Actualizar datos de la curva en la UI
        self.curve.setData(self.display_buffer)

    def closeEvent(self, event):
        """Asegurar cierre limpio de hilos al cerrar la ventana"""
        self.data_source.stop()
        self.data_source.wait()
        event.accept()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    
    # Estilo Dark Mode para la app
    app.setStyle("Fusion")
    
    win = OscilloscopeUI()
    win.show()
    sys.exit(app.exec_())