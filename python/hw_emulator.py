import sys
import time
import struct
import socket
import numpy as np
from PyQt5 import QtWidgets, QtCore
from theme import get_stylesheet

BAUDRATE = 921600
SAMPLES_PER_BUFFER = 1024
ADC_MAX_VAL = 4095
DEFAULT_TCP_PORT = 5555

class EmulatorWorker(QtCore.QThread):
    status_signal = QtCore.pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.server = None
        self.conn = None
        
        # Generator Parameters
        self.waveform = "Sine" # "Sine", "Square", "Triangle", "Noise"
        self.amplitude = 1500
        self.offset = 2048
        self.noise_level = 15
        self.speed = 0.1
        self.frequency = 1.0
        self.fps = 50.0

    def start_server(self, port):
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind(("127.0.0.1", port))
            self.server.listen(1)
            self.server.settimeout(1.0) # non-blocking accept
            self.status_signal.emit(f"Waiting for connection on TCP {port}...")
            self.running = True
            self.start()
        except Exception as e:
            self.status_signal.emit(f"Error starting server: {e}")

    def stop_server(self):
        self.running = False
        self.wait()
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
            self.conn = None
        if self.server:
            try:
                self.server.close()
            except:
                pass
            self.server = None
        self.status_signal.emit("Server stopped.")

    def run(self):
        while self.running:
            # 1. Accept Connection
            while self.running and not self.conn:
                try:
                    self.conn, addr = self.server.accept()
                    self.status_signal.emit(f"Connected to GUI at {addr[0]}:{addr[1]}")
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        self.status_signal.emit(f"Accept error: {e}")
                    return

            seq_id = 0
            phase = 0.0
            start_time = time.time()

            # 2. Transmit loop
            while self.running and self.conn:
                t = np.linspace(phase, phase + 2*np.pi * self.frequency, SAMPLES_PER_BUFFER)
                
                if self.waveform == "Sine":
                    base_wave = np.sin(t)
                elif self.waveform == "Square":
                    base_wave = np.sign(np.sin(t))
                elif self.waveform == "Triangle":
                    base_wave = 2/np.pi * np.arcsin(np.sin(t))
                elif self.waveform == "Noise":
                    base_wave = np.zeros_like(t)
                else:
                    base_wave = np.sin(t)

                noise = np.random.normal(0, self.noise_level, SAMPLES_PER_BUFFER)
                
                samples = (self.offset + self.amplitude * base_wave + noise)
                samples = np.clip(samples, 0, ADC_MAX_VAL).astype(np.uint16)

                timestamp = int((time.time() - start_time) * 1000)
                metadata = struct.pack('<IIBB', seq_id, timestamp, 0, 0)

                meta_words = np.frombuffer(metadata, dtype='<H')
                calc_crc = int(np.bitwise_xor.reduce(meta_words) ^ np.bitwise_xor.reduce(samples))
                crc_bytes = struct.pack('<H', calc_crc)

                frame = b'\xaa\x55' + metadata + samples.tobytes() + crc_bytes
                
                try:
                    self.conn.sendall(frame)
                except Exception as e:
                    self.status_signal.emit(f"Client disconnected: {e}")
                    self.conn.close()
                    self.conn = None
                    self.status_signal.emit(f"Waiting for connection on TCP...")
                    break

                seq_id += 1
                phase += self.speed
                time.sleep(1.0 / self.fps)

class EmulatorUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pico-OS | Virtual Signal Generator")
        self.resize(850, 350)
        self.setStyleSheet(get_stylesheet())

        self.worker = EmulatorWorker()
        self.worker.status_signal.connect(self.update_status)

        self.init_ui()

    def init_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QVBoxLayout(central)

        # --- TOP ROW (Server & Waveforms) ---
        top_layout = QtWidgets.QHBoxLayout()
        top_layout.setSpacing(20)

        # Connection Group
        conn_group = QtWidgets.QGroupBox("Server Configuration")
        conn_layout = QtWidgets.QHBoxLayout(conn_group)
        conn_layout.setContentsMargins(15, 20, 15, 15)
        self.port_input = QtWidgets.QLineEdit(str(DEFAULT_TCP_PORT))
        self.port_input.setPlaceholderText("TCP Port")
        self.port_input.setFixedWidth(80)
        self.btn_start = QtWidgets.QPushButton("Start Server")
        self.btn_start.clicked.connect(self.toggle_server)
        conn_layout.addWidget(QtWidgets.QLabel("Port:"))
        conn_layout.addWidget(self.port_input)
        conn_layout.addWidget(self.btn_start)
        top_layout.addWidget(conn_group)

        # Waveform Group
        wave_group_box = QtWidgets.QGroupBox("Waveform")
        wave_layout = QtWidgets.QHBoxLayout(wave_group_box)
        wave_layout.setContentsMargins(15, 20, 15, 15)
        wave_layout.setSpacing(8)
        self.wave_group = QtWidgets.QButtonGroup()
        waves = ["Sine", "Square", "Triangle", "Noise"]
        for i, name in enumerate(waves):
            btn = QtWidgets.QPushButton(name)
            btn.setCheckable(True)
            btn.setMinimumHeight(35)
            btn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            btn.setStyleSheet("""
                QPushButton { background-color: #2d2d2d; border-radius: 4px; border: 1px solid #444; font-weight: normal; font-size: 13px; }
                QPushButton:checked { background-color: #0d6efd; color: white; border: 1px solid #0b5ed7; font-weight: bold; }
            """)
            self.wave_group.addButton(btn, i)
            wave_layout.addWidget(btn)
            if name == "Sine":
                btn.setChecked(True)
        self.wave_group.buttonClicked.connect(self.update_params)
        top_layout.addWidget(wave_group_box, stretch=1)

        main_layout.addLayout(top_layout)

        # --- BOTTOM ROW (Knobs) ---
        gen_group = QtWidgets.QGroupBox("Signal Parameters")
        knobs_layout = QtWidgets.QHBoxLayout(gen_group)
        knobs_layout.setSpacing(20)
        knobs_layout.setContentsMargins(15, 20, 15, 15)

        # Frequency Knob
        self.freq_mult = QtWidgets.QComboBox()
        self.freq_mult.addItems(["x1 (Cycles)", "x10", "x100", "kHz (True Hz)", "MHz"])
        self.freq_mult.currentIndexChanged.connect(self.update_params)
        
        self.freq_slider, freq_widget = self.create_knob_widget("Frequency", 1, 999, 1, self.update_params, mult_combo=self.freq_mult)
        knobs_layout.addWidget(freq_widget)

        # Amplitude Knob
        self.amp_slider, amp_widget = self.create_knob_widget("Amplitude", 0, 2048, 1500, self.update_params)
        knobs_layout.addWidget(amp_widget)

        # Offset Knob
        self.offset_slider, off_widget = self.create_knob_widget("DC Offset", 0, 4095, 2048, self.update_params)
        knobs_layout.addWidget(off_widget)

        # Noise Knob
        self.noise_slider, noise_widget = self.create_knob_widget("Noise Level", 0, 500, 15, self.update_params)
        knobs_layout.addWidget(noise_widget)

        # Speed Knob
        self.speed_slider, speed_widget = self.create_knob_widget("Phase Speed", 1, 100, 10, self.update_params)
        knobs_layout.addWidget(speed_widget)

        main_layout.addWidget(gen_group)

        self.status_label = QtWidgets.QLabel("Status: Stopped")
        self.status_label.setStyleSheet("color: #aaaaaa; font-style: italic; margin-top: 5px; font-size: 12px;")
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        main_layout.addWidget(self.status_label)

        main_layout.addStretch()

    def create_knob_widget(self, name, vmin, vmax, vinit, callback, mult_combo=None):
        group = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(group)
        layout.setAlignment(QtCore.Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        
        title = QtWidgets.QLabel(name)
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("font-weight: bold; color: #e0e0e0; margin-bottom: 2px;")
        
        lcd = QtWidgets.QLCDNumber()
        lcd.setSegmentStyle(QtWidgets.QLCDNumber.Flat)
        lcd.setStyleSheet("background-color: #111; color: #0d6efd; border: 1px solid #333; border-radius: 4px;")
        lcd.setFixedHeight(30)
        lcd.display(vinit)
        
        dial = QtWidgets.QDial()
        dial.setMinimum(vmin)
        dial.setMaximum(vmax)
        dial.setValue(vinit)
        dial.setNotchesVisible(True)
        dial.setFixedSize(80, 80)
        dial.setStyleSheet("background-color: #0d6efd;")
        
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(5)
        
        btn_down = QtWidgets.QPushButton("-")
        btn_down.setFixedSize(24, 24)
        btn_down.setStyleSheet("padding: 0px; font-size: 16px; border-radius: 4px; background-color: #333;")
        btn_down.clicked.connect(lambda: dial.setValue(dial.value() - 1))
        
        btn_up = QtWidgets.QPushButton("+")
        btn_up.setFixedSize(24, 24)
        btn_up.setStyleSheet("padding: 0px; font-size: 16px; border-radius: 4px; background-color: #333;")
        btn_up.clicked.connect(lambda: dial.setValue(dial.value() + 1))
        
        btn_layout.addWidget(btn_down)
        if mult_combo:
            btn_layout.addWidget(mult_combo)
        else:
            btn_layout.addStretch()
        btn_layout.addWidget(btn_up)
        
        def on_change(val):
            lcd.display(val)
            callback()
            
        dial.valueChanged.connect(on_change)
        
        layout.addWidget(title)
        layout.addWidget(lcd)
        layout.addWidget(dial, 0, QtCore.Qt.AlignCenter)
        layout.addLayout(btn_layout)
        
        return dial, group

    def update_params(self):
        waves_names = ["Sine", "Square", "Triangle", "Noise"]
        self.worker.waveform = waves_names[self.wave_group.checkedId()]
        
        val = self.freq_slider.value()
        mult = self.freq_mult.currentText()
        
        # Calculate cycles per buffer based on selection
        if mult.startswith("x1 ("):
            f = val
        elif mult == "x10":
            f = val * 10
        elif mult == "x100":
            f = val * 100
        elif mult.startswith("kHz"):
            # Assume 500kS/s sample rate and 1024 samples/buffer -> 1 buffer = 2.048ms
            # 1 Hz = 0.002048 cycles/buffer
            f = val * 1000 * 0.002048
        elif mult == "MHz":
            f = val * 1000000 * 0.002048
        else:
            f = val
            
        self.worker.frequency = f
        self.worker.amplitude = self.amp_slider.value()
        self.worker.offset = self.offset_slider.value()
        self.worker.noise_level = self.noise_slider.value()
        self.worker.speed = self.speed_slider.value() / 100.0

    def toggle_server(self):
        if self.worker.running:
            self.worker.stop_server()
            self.btn_start.setText("Start Server")
            self.port_input.setEnabled(True)
        else:
            try:
                port = int(self.port_input.text())
                self.worker.start_server(port)
                self.btn_start.setText("Stop Server")
                self.port_input.setEnabled(False)
            except ValueError:
                self.update_status("Invalid port number.")

    def update_status(self, msg):
        self.status_label.setText(f"Status: {msg}")

    def closeEvent(self, event):
        self.worker.stop_server()
        event.accept()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    win = EmulatorUI()
    win.show()
    sys.exit(app.exec_())
