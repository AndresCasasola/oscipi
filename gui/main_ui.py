import sys
import time
import struct
import numpy as np
import serial
import serial.tools.list_ports
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg

# --- GLOBAL BUNKER CONFIGURATION ---
SIMULATE_MODE = False  # Change to False to connect to the real Pico
BAUDRATE = 921600
SAMPLES_PER_BUFFER = 1024
DISPLAY_CHUNKS = 5     # How many buffers we want to see on screen at once
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

class SerialPicoSource(DataSource):
    """Real Driver: Reads the framing protocol defined for the bunker"""
    def run(self):
        try:
            with serial.Serial(self.port, BAUDRATE, timeout=1) as ser:
                while self.running:
                    # Search for sync header 0xAA 0x55
                    if ser.read(1) == b'\xaa':
                        if ser.read(1) == b'\x55':
                            # Read metadata: ID (4) + Timestamp (4) + Flags (1) + Pad (1) = 10 bytes
                            metadata = ser.read(10) 
                            if len(metadata) < 10:
                                continue
                            
                            seq_id, timestamp, flags, pad = struct.unpack('<IIBB', metadata)
                            
                            # Read 1024 samples (2 bytes each = 2048 bytes)
                            raw_payload = ser.read(SAMPLES_PER_BUFFER * 2)
                            if len(raw_payload) < SAMPLES_PER_BUFFER * 2:
                                continue
                                
                            # Read checksum (2 bytes)
                            crc_bytes = ser.read(2)
                            if len(crc_bytes) < 2:
                                continue
                            
                            expected_crc = struct.unpack('<H', crc_bytes)[0]
                            
                            # Ultra-fast bytes to NumPy conversion (16-bit unsigned)
                            samples = np.frombuffer(raw_payload, dtype='<H')
                            
                            # Fast XOR Checksum calculation using NumPy
                            meta_words = np.frombuffer(metadata, dtype='<H')
                            calc_crc = np.bitwise_xor.reduce(meta_words) ^ np.bitwise_xor.reduce(samples)
                            
                            # Convert to native integer to avoid numpy type issues
                            calc_crc = int(calc_crc) 
                            
                            if calc_crc == expected_crc:
                                # If overflow is reported by the Pico
                                if flags & 0x01:
                                    print(f"Warning: Hardware Overflow detected at sequence {seq_id}")
                                if flags & 0x02:
                                    print(f"Warning: Gap detected (Firmware dropped a frame) at sequence {seq_id}")
                                
                                self.new_data_signal.emit(samples)
                            else:
                                print(f"CRC Error! Drop frame {seq_id}. Expected: {expected_crc}, Calc: {calc_crc}")
        except Exception as e:
            print(f"CRITICAL UART ERROR: {e}")

# --- GRAPHICAL INTERFACE LAYER (PYQTGRAPH) ---

class OscilloscopeUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # 1. Window Configuration
        self.setWindowTitle("Pico-OS | Professional Real-Time Oscilloscope")
        self.resize(1100, 700)
        self.setStyleSheet("background-color: #121212; color: #E0E0E0;")

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
        
        self.control_layout.addWidget(QtWidgets.QLabel("COM Port:"))
        self.control_layout.addWidget(self.port_combo)
        self.control_layout.addWidget(self.refresh_btn)
        self.control_layout.addWidget(self.connect_btn)
        self.control_layout.addStretch()
        
        self.main_layout.addLayout(self.control_layout)

        # 4. Plot Widget
        self.plot_widget = pg.PlotWidget(title="ADC Signal Stream")
        self.plot_widget.setYRange(0, ADC_MAX_VAL)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)
        self.plot_widget.getAxis('left').setLabel('Amplitude', units='ADC Units')
        self.plot_widget.getAxis('bottom').setLabel('Samples')
        
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

    def refresh_ports(self):
        """Scans for available serial ports and populates the dropdown"""
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for p in ports:
            # Add item with a descriptive name, but store the actual device path (e.g. 'COM3') as the item data
            self.port_combo.addItem(f"{p.device} - {p.description}", p.device)

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
        """Updates the plot with the new data block"""
        # Shift the buffer to the left and append the new data at the end
        self.display_buffer = np.roll(self.display_buffer, -SAMPLES_PER_BUFFER)
        self.display_buffer[-SAMPLES_PER_BUFFER:] = new_samples
        
        # Update curve data in the UI
        self.curve.setData(self.display_buffer)

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