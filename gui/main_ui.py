import sys
import numpy as np
import pyqtgraph as pg
from PyQt5 import QtWidgets, QtCore

class OscilloscopeUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # 1. Configuración de la Ventana Principal
        self.setWindowTitle("Pico OS - Digital Oscilloscope")
        self.resize(800, 600)

        # 2. Widget Central y Layout
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QtWidgets.QVBoxLayout(self.central_widget)

        # 3. Inicialización de la Gráfica (PyQtGraph)
        self.plot_widget = pg.PlotWidget(title="Live ADC Signal")
        self.plot_widget.setBackground('k')  # Fondo negro (estilo osciloscopio)
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setLabel('left', 'Voltage', units='V')
        self.plot_widget.setLabel('bottom', 'Time', units='s')
        
        # El objeto que representa la línea de la gráfica
        self.curve = self.plot_widget.plot(pen=pg.mkPen('g', width=2)) 

        self.layout.addWidget(self.plot_widget)

        # 4. Buffer de Datos
        self.buffer_size = 500
        self.data_buffer = np.zeros(self.buffer_size)

        # 5. Timer para el Refresh (Simulando recepción UART)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(20)  # ~50 FPS (20ms)

    def update_plot(self):
        """
        Aquí es donde integraremos la lectura serial más adelante.
        Por ahora, simulamos una señal con ruido.
        """
        # Desplazamos los datos (scroll)
        self.data_buffer[:-1] = self.data_buffer[1:]
        
        # Simulamos la entrada: Aquí irá el valor que leas de la Pico
        new_sample = np.sin(np.pi * QtCore.QTime.currentTime().msec() / 100) + np.random.normal(0, 0.1)
        self.data_buffer[-1] = new_sample

        # Actualizamos la gráfica
        self.curve.setData(self.data_buffer)

    def setup_controls(self):
        """
        Espacio reservado para añadir botones, sliders de ganancia, 
        selectores de puerto COM, etc.
        """
        pass

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = OscilloscopeUI()
    window.show()
    sys.exit(app.exec_())