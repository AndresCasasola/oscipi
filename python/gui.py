import sys
import time
import struct
import numpy as np
import socket
import serial
import serial.tools.list_ports
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg
from theme import get_stylesheet

# --- GLOBAL BUNKER CONFIGURATION ---
SIMULATE_MODE = False  # Change to False to connect to the real Pico
BAUDRATE = 921600
SAMPLES_PER_BUFFER = 1024
DISPLAY_CHUNKS = 50     # How many buffers we want to see on screen at once (50 = 1 full second at 50FPS)
ADC_MAX_VAL = 4095     # 12-bit resolution of the Pico

# --- DATA LAYER (MODULARIZED) ---

class DataSource(QtCore.QThread):
    """Base interface for data sources"""
    new_data_signal = QtCore.pyqtSignal(np.ndarray)
    
    def __init__(self):
        super().__init__()
        self.running = True

    def stop(self):
        self.running = False

class MockPicoSource(DataSource):
    """Simulator: Generates a sine wave with noise for hardware-less testing"""
    def run(self):
        phase = 0.0
        while self.running:
            # Generate time and wave
            t = np.linspace(phase, phase + 2*np.pi, SAMPLES_PER_BUFFER)
            
            # 2048 is the ADC center (3.3V / 2), 1500 is the amplitude
            noise = np.random.normal(0, 15, SAMPLES_PER_BUFFER)
            samples = (2048 + 1500 * np.sin(t) + noise).astype(np.uint16)
            
            # Clip to ensure it doesn't exceed the ADC range
            samples = np.clip(samples, 0, ADC_MAX_VAL)
            
            self.new_data_signal.emit(samples)
            
            phase += 0.1 # Wave movement speed
            time.sleep(0.02) # ~50 FPS for total smoothness

class TCPSerialWrapper:
    """Mocks a pyserial Serial object but uses a TCP socket internally."""
    def __init__(self, port_str, timeout=1):
        # Expects "tcp:host:port"
        parts = port_str.split(":")
        host = parts[1]
        port = int(parts[2])
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.connect((host, port))
        
    def setDTR(self, val): pass
    def setRTS(self, val): pass
    
    def read(self, size=1):
        try:
            data = b''
            while len(data) < size:
                chunk = self.sock.recv(size - len(data))
                if not chunk:
                    break
                data += chunk
            return data
        except socket.timeout:
            return b''

    def close(self):
        self.sock.close()
        
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): self.close()

class SerialPicoSource(DataSource):
    """Real Driver: Reads the framing protocol and monitors transfer performance"""
    def run(self):
        # Performance monitoring variables
        bytes_received_total = 0
        frames_received_total = 0
        first_frame_seen = False
        start_perf_time = time.time()
        
        try:
            if self.port.startswith("tcp:"):
                context = TCPSerialWrapper(self.port, timeout=1)
            else:
                context = serial.Serial(self.port, BAUDRATE, timeout=1)

            with context as ser:
                ser.setDTR(True)
                ser.setRTS(True)
                print(f"--- CONNECTED TO {self.port} ---")
                
                while self.running:
                    byte1 = ser.read(1)
                    if byte1 == b'\xaa':
                        byte2 = ser.read(1)
                        if byte2 == b'\x55':
                            # 1. Read metadata (10 bytes)
                            metadata = ser.read(10) 
                            if len(metadata) < 10: continue
                            
                            seq_id, timestamp, flags, pad = struct.unpack('<IIBB', metadata)
                            
                            # 2. Read samples (2048 bytes)
                            raw_payload = ser.read(SAMPLES_PER_BUFFER * 2)
                            if len(raw_payload) < SAMPLES_PER_BUFFER * 2: continue
                                
                            # 3. Read checksum (2 bytes)
                            crc_bytes = ser.read(2)
                            if len(crc_bytes) < 2: continue
                            
                            expected_crc = struct.unpack('<H', crc_bytes)[0]
                            
                            # 4. Process and Emit
                            samples = np.frombuffer(raw_payload, dtype='<H')
                            meta_words = np.frombuffer(metadata, dtype='<H')
                            calc_crc = int(np.bitwise_xor.reduce(meta_words) ^ np.bitwise_xor.reduce(samples))
                            
                            if calc_crc == expected_crc:
                                self.new_data_signal.emit(samples)
                                bytes_received_total += (14 + SAMPLES_PER_BUFFER * 2)
                                frames_received_total += 1
                                
                                if not first_frame_seen:
                                    print("--- FIRST VALID FRAME RECEIVED SUCCESSFULLY! ---")
                                    first_frame_seen = True
                            else:
                                print(f"CRC Error! Frame {seq_id}")

                    # --- Performance Reporting ---
                    current_time = time.time()
                    if current_time - start_perf_time >= 1.0:
                        elapsed = current_time - start_perf_time
                        kbps = (bytes_received_total / 1024) / elapsed
                        fps = frames_received_total / elapsed
                        
                        # Monitor simple de consola (sin acceder a la cola para evitar el error)
                        print(f"| [THROUGHPUT] {kbps:>7.2f} KB/s | [FPS] {fps:>5.1f} frames/s |")
                        
                        bytes_received_total = 0
                        frames_received_total = 0
                        start_perf_time = current_time

        except Exception as e:
            print(f"CRITICAL UART ERROR: {e}")

# --- GRAPHICAL INTERFACE LAYER (PYQTGRAPH) ---

class OscilloscopeUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # 1. Window Configuration
        self.setWindowTitle("Pico-OS | Professional Real-Time Oscilloscope")
        self.resize(1100, 700)
        self.setStyleSheet(get_stylesheet())

        # 2. Main Layout
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QtWidgets.QVBoxLayout(self.central_widget)

        # 3. Top Control Bar
        self.control_layout = QtWidgets.QHBoxLayout()
        
        self.port_combo = QtWidgets.QComboBox()
        self.port_combo.setMinimumWidth(250)
        self.refresh_ports()
        
        self.refresh_btn = QtWidgets.QPushButton("Refresh Ports")
        self.refresh_btn.clicked.connect(self.refresh_ports)
        
        self.connect_btn = QtWidgets.QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)
        
        self.voltage_spin = QtWidgets.QDoubleSpinBox()
        self.voltage_spin.setRange(0.1, 100.0)
        self.voltage_spin.setValue(3.3)
        self.voltage_spin.setSingleStep(0.1)
        self.voltage_spin.setSuffix(" V")
        self.voltage_spin.valueChanged.connect(self.update_y_range)
        
        self.timebase_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.timebase_slider.setMinimum(100)
        self.timebase_slider.setMaximum(SAMPLES_PER_BUFFER * DISPLAY_CHUNKS)
        # Default to a medium zoom (e.g., 5 chunks = 5120 samples) so it's not too squished on startup
        self.timebase_slider.setValue(SAMPLES_PER_BUFFER * 5)
        self.timebase_slider.setMinimumWidth(250)
        self.timebase_slider.valueChanged.connect(self.update_timebase)
        
        self.control_layout.addWidget(QtWidgets.QLabel("COM Port:"))
        self.control_layout.addWidget(self.port_combo)
        self.control_layout.addWidget(self.refresh_btn)
        self.control_layout.addWidget(self.connect_btn)
        
        self.control_layout.addSpacing(20)
        self.control_layout.addWidget(QtWidgets.QLabel("ADC Range:"))
        self.control_layout.addWidget(self.voltage_spin)
        
        # Add some spacing before time scale
        self.control_layout.addSpacing(20)
        self.control_layout.addWidget(QtWidgets.QLabel("Time Scale (Zoom):"))
        self.control_layout.addWidget(self.timebase_slider)
        
        self.control_layout.addStretch()
        
        self.main_layout.addLayout(self.control_layout)

        # 4. Plot Widget
        self.plot_widget = pg.PlotWidget(title="Real-Time Signal Stream")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)
        self.plot_widget.getAxis('left').setLabel('Amplitude', units='V')
        self.plot_widget.getAxis('bottom').setLabel('Samples')
        self.update_y_range()
        
        # Disable auto-range on X to allow manual zooming, but keep Y fixed
        self.plot_widget.setMouseEnabled(x=False, y=False) 
        self.update_timebase(self.timebase_slider.value())
        
        # Curve style (Classic oscilloscope bright green)
        self.curve = self.plot_widget.plot(pen=pg.mkPen(color='#39FF14', width=1.5))
        self.main_layout.addWidget(self.plot_widget)

        # 5. Display Buffer (Persistence effect)
        self.display_buffer = np.full(SAMPLES_PER_BUFFER * DISPLAY_CHUNKS, 2048)

        # 6. Data Source Initialization
        self.data_source = None
        if SIMULATE_MODE:
            self.port_combo.setEnabled(False)
            self.refresh_btn.setEnabled(False)
            self.connect_btn.setEnabled(False)
            self.start_simulation()
        else:
            self.statusBar().showMessage("DISCONNECTED - Please select a COM port and connect.")

    def update_timebase(self, value):
        """Updates the X-axis range to zoom into the latest samples on the right side of the screen."""
        max_idx = SAMPLES_PER_BUFFER * DISPLAY_CHUNKS
        # Zoom into the newest data at the end of the buffer
        self.plot_widget.setXRange(max_idx - value, max_idx, padding=0)

    def update_y_range(self):
        """Updates the Y-axis range based on the configured ADC max voltage."""
        v_max = self.voltage_spin.value()
        self.plot_widget.setYRange(0, v_max)

    def refresh_ports(self):
        """Scans for available serial ports and populates the dropdown"""
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for p in ports:
            # Add item with a descriptive name, but store the actual device path (e.g. 'COM3') as the item data
            self.port_combo.addItem(f"{p.device} - {p.description}", p.device)
        self.port_combo.addItem("TCP Localhost:5555 (Emulator)", "tcp:127.0.0.1:5555")

    def toggle_connection(self):
        """Connects or disconnects the serial data source"""
        if self.data_source is not None and self.data_source.isRunning():
            # Stop the source if it's running
            self.data_source.stop()
            self.data_source.wait()
            self.data_source = None
            self.connect_btn.setText("Connect")
            self.port_combo.setEnabled(True)
            self.refresh_btn.setEnabled(True)
            self.statusBar().showMessage("DISCONNECTED")
        else:
            # Start the connection
            if self.port_combo.count() == 0:
                self.statusBar().showMessage("ERROR: No COM port selected.")
                return
                
            port = self.port_combo.currentData()
            self.data_source = SerialPicoSource()
            self.data_source.port = port
            self.data_source.new_data_signal.connect(self.update_plot)
            self.data_source.start()
            
            self.connect_btn.setText("Disconnect")
            self.port_combo.setEnabled(False)
            self.refresh_btn.setEnabled(False)
            self.statusBar().showMessage(f"CONNECTED TO: {port}")

    def start_simulation(self):
        """Starts the mock source for testing without hardware"""
        self.data_source = MockPicoSource()
        self.data_source.new_data_signal.connect(self.update_plot)
        self.data_source.start()
        self.statusBar().showMessage("SIMULATION MODE ACTIVE (No Hardware)")

    def update_plot(self, new_samples):
        """Immediately renders the new hardware frame to screen for zero-latency plotting."""
        # Shift the display buffer to the left and append the new 1024 samples
        self.display_buffer = np.roll(self.display_buffer, -SAMPLES_PER_BUFFER)
        self.display_buffer[-SAMPLES_PER_BUFFER:] = new_samples
        
        # Convert raw ADC values to Voltage
        v_max = self.voltage_spin.value()
        voltage_data = (self.display_buffer / ADC_MAX_VAL) * v_max
        
        # Update curve data in the UI
        self.curve.setData(voltage_data)

    def closeEvent(self, event):
        """Ensure clean thread shutdown when closing the window"""
        if self.data_source is not None:
            self.data_source.stop()
            self.data_source.wait()
        event.accept()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    
    # Dark Mode style for the app
    app.setStyle("Fusion")
    
    win = OscilloscopeUI()
    win.show()
    sys.exit(app.exec_())