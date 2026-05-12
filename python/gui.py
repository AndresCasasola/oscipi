import sys
import time
import struct
import numpy as np
import socket
import serial
import serial.tools.list_ports
import os
import json
from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
from theme import get_stylesheet

# --- GLOBAL BUNKER CONFIGURATION ---
SIMULATE_MODE = False  # Change to False to connect to the real Pico
BAUDRATE = 921600
SAMPLES_PER_BUFFER = 1024
DISPLAY_CHUNKS = 50     # How many buffers we want to see on screen at once (50 = 1 full second at 50FPS)
ADC_MAX_VAL = 4095     # 12-bit resolution of the Pico

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except: pass
    return {"ram_limit_gb": 1.0}

def save_config(cfg):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=4)

# --- DATA LAYER (MODULARIZED) ---

class DataSource(QtCore.QThread):
    """Base interface for data sources"""
    new_data_signal = QtCore.pyqtSignal(dict)
    error_signal = QtCore.pyqtSignal(str)
    
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
            
            packet = {
                'seq': int(phase * 10),
                'time': int(time.time() * 1e6),
                'flags': 0,
                'crc': 0xABCD,
                'samples': samples
            }
            self.new_data_signal.emit(packet)
            
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
    def __init__(self):
        super().__init__()
        self.streaming = True   # When False, port stays open but data is discarded

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
                            # 1. Read Telemetry (20 bytes)
                            telemetry_raw = ser.read(20)
                            if len(telemetry_raw) < 20: continue
                            t_dma, t_meta, t_chk, t_usb, t_loop = struct.unpack('<IIIII', telemetry_raw)
                            
                            # 2. Read metadata (10 bytes)
                            metadata = ser.read(10) 
                            if len(metadata) < 10: continue
                            
                            seq_id, timestamp, flags, pad = struct.unpack('<IIBB', metadata)
                            
                            # 3. Read samples (2048 bytes)
                            raw_payload = ser.read(SAMPLES_PER_BUFFER * 2)
                            if len(raw_payload) < SAMPLES_PER_BUFFER * 2: continue
                                
                            # 4. Read checksum (2 bytes)
                            crc_bytes = ser.read(2)
                            if len(crc_bytes) < 2: continue
                            
                            expected_crc = struct.unpack('<H', crc_bytes)[0]

                            # Discard frame if not streaming
                            if not self.streaming:
                                continue
                            
                            # 5. Process and Emit
                            samples = np.frombuffer(raw_payload, dtype='<H')
                            meta_words = np.frombuffer(metadata, dtype='<H')
                            calc_crc = int(np.bitwise_xor.reduce(meta_words) ^ np.bitwise_xor.reduce(samples))
                            
                            if calc_crc == expected_crc:
                                packet = {
                                    'seq': seq_id,
                                    'time': timestamp,
                                    'flags': flags,
                                    'crc': expected_crc,
                                    'samples': samples,
                                    'telemetry': {
                                        'dma_us': t_dma,
                                        'metadata_us': t_meta,
                                        'checksum_us': t_chk,
                                        'usb_transport_us': t_usb,
                                        'total_loop_us': t_loop
                                    }
                                }
                                self.new_data_signal.emit(packet)
                                bytes_received_total += (34 + SAMPLES_PER_BUFFER * 2)
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
                        print(f"| [THROUGHPUT] {kbps:>7.2f} KB/s | [FPS] {fps:>5.1f} frames/s |")
                        bytes_received_total = 0
                        frames_received_total = 0
                        start_perf_time = current_time

        except Exception as e:
            print(f"CRITICAL UART ERROR: {e}")
            self.error_signal.emit(str(e))

# --- PACKET INSPECTOR MODEL ---

class PacketTableModel(QtCore.QAbstractTableModel):
    def __init__(self, ui):
        super().__init__()
        self.ui = ui
        self.headers = ["Index", "Seq ID", "Time (us)", "Flags", "CRC"]

    def rowCount(self, parent=QtCore.QModelIndex()):
        if self.ui.hist_count == 0: return 0
        return self.ui.hist_count + 1 # +1 for AVERAGE row at index 0

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self.headers)
        
    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid(): return None
        row = index.row()
        col = index.column()

        if role == QtCore.Qt.BackgroundRole:
            if row == 0:
                return QtGui.QColor("#0d1a2a") # Dark blue for average row
            return None

        if role == QtCore.Qt.ForegroundRole:
            if row == 0:
                return QtGui.QColor("#3D8EFF") # Bright blue text
            return None

        if role == QtCore.Qt.DisplayRole:
            if row == 0:
                if col == 0: return "\u03A3" # Sigma
                if col == 1: return "HISTORY AVERAGE"
                if col == 2: return f"{self.ui.hist_count} pkts"
                return "-"
            
            # Normal rows (offset by 1)
            row_idx = row - 1
            if self.ui.hist_count < self.ui.max_packets:
                phys_idx = row_idx
            else:
                phys_idx = (self.ui.hist_head + row_idx) % self.ui.max_packets
                
            if col == 0: return str(row_idx)
            if col == 1: return str(self.ui.hist_seq[phys_idx])
            if col == 2: return str(self.ui.hist_time[phys_idx])
            if col == 3: return f"0x{self.ui.hist_flags[phys_idx]:02X}"
            if col == 4: return f"0x{self.ui.hist_crc[phys_idx]:04X}"
        return None

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return self.headers[section]
        return None

# --- GRAPHICAL INTERFACE LAYER (PYQTGRAPH) ---

class OscilloscopeUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # 1. Window Configuration
        self.setWindowTitle("Oscipi | Professional Real-Time Oscilloscope")
        
        # Set Window Icon
        icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QtGui.QIcon(icon_path))
            
        self.resize(1600, 950)
        self.setStyleSheet(get_stylesheet())
        
        # Init Config & Memory
        self.config = load_config()
        self.init_history_buffer()

        # 2. Main Layout
        self.tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Setup Tabs
        self.setup_osc_tab()
        self.setup_inspector_tab()
        
        # 6. Data Source Initialization
        self.data_source = None
        if SIMULATE_MODE:
            self.port_combo.setEnabled(False)
            self.refresh_btn.setEnabled(False)
            self.connect_btn.setEnabled(False)
            self.start_simulation()

        # Global connection bar at bottom
        self._build_global_connection_bar()

    def init_history_buffer(self):
        # Calculate max packets based on RAM limit.
        ram_gb = self.config.get("ram_limit_gb", 1.0)
        bytes_per_packet = (SAMPLES_PER_BUFFER * 2) + 4 + 4 + 1 + 2 + 20
        total_bytes = ram_gb * 1073741824
        self.max_packets = int(total_bytes / bytes_per_packet)
        
        print(f"Pre-allocating RAM for {self.max_packets} packets ({ram_gb} GB)...")
        
        self.hist_samples = np.empty((self.max_packets, SAMPLES_PER_BUFFER), dtype=np.uint16)
        self.hist_seq = np.empty(self.max_packets, dtype=np.uint32)
        self.hist_time = np.empty(self.max_packets, dtype=np.uint32)
        self.hist_flags = np.empty(self.max_packets, dtype=np.uint8)
        self.hist_crc = np.empty(self.max_packets, dtype=np.uint16)
        
        self.hist_tel_dma = np.empty(self.max_packets, dtype=np.uint32)
        self.hist_tel_meta = np.empty(self.max_packets, dtype=np.uint32)
        self.hist_tel_chk = np.empty(self.max_packets, dtype=np.uint32)
        self.hist_tel_usb = np.empty(self.max_packets, dtype=np.uint32)
        self.hist_tel_loop = np.empty(self.max_packets, dtype=np.uint32)
        
        self.hist_head = 0
        self.hist_count = 0
        print("RAM Allocation complete.")

    def setup_osc_tab(self):
        osc_tab = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout(osc_tab)
        
        # Top Control Bar (oscilloscope-specific: ADC range + zoom only)
        control_layout = QtWidgets.QHBoxLayout()
        control_layout.setContentsMargins(6, 3, 6, 3)
        
        self.clear_osc_btn = QtWidgets.QPushButton("Clear Display")
        self.clear_osc_btn.clicked.connect(self.clear_oscilloscope)
        
        self.voltage_spin = QtWidgets.QDoubleSpinBox()
        self.voltage_spin.setRange(0.1, 100.0)
        self.voltage_spin.setValue(3.3)
        self.voltage_spin.setSingleStep(0.1)
        self.voltage_spin.setSuffix(" V")
        self.voltage_spin.valueChanged.connect(self.update_y_range)
        
        self.timebase_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.timebase_slider.setMinimum(100)
        self.timebase_slider.setMaximum(SAMPLES_PER_BUFFER * DISPLAY_CHUNKS)
        self.timebase_slider.setValue(SAMPLES_PER_BUFFER * 5)
        self.timebase_slider.setMinimumWidth(250)
        self.timebase_slider.valueChanged.connect(self.update_timebase)
        
        control_layout.addWidget(self.clear_osc_btn)
        control_layout.addSpacing(20)
        control_layout.addWidget(QtWidgets.QLabel("ADC Range:"))
        control_layout.addWidget(self.voltage_spin)
        control_layout.addSpacing(20)
        control_layout.addWidget(QtWidgets.QLabel("Time Scale (Zoom):"))
        control_layout.addWidget(self.timebase_slider)
        control_layout.addStretch()
        
        control_container = QtWidgets.QWidget()
        control_container.setObjectName("controlBar")
        control_container.setStyleSheet("""
            QWidget#controlBar {
                background-color: #0d0d1a;
                border-bottom: 1px solid #1a2a4a;
            }
        """)
        control_container.setLayout(control_layout)
        main_layout.addWidget(control_container)

        # 4. Plot Widget
        self.plot_widget = pg.PlotWidget(title="Real-Time Signal Stream")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)
        self.plot_widget.getAxis('left').setLabel('Amplitude', units='V')
        self.plot_widget.getAxis('bottom').setLabel('Time', units='ms')
        
        # Disable auto-range on X to allow manual zooming, but keep Y fixed
        self.plot_widget.setMouseEnabled(x=False, y=False) 
        
        # Curve style (Classic oscilloscope bright green)
        self.curve = self.plot_widget.plot(pen=pg.mkPen(color='#39FF14', width=1.5))
        main_layout.addWidget(self.plot_widget)

        # 5. Display Buffer (Persistence effect)
        total_samples = SAMPLES_PER_BUFFER * DISPLAY_CHUNKS
        self.display_buffer = np.full(total_samples, 2048)
        
        # Create Time Array (X-axis) in milliseconds based on 500 kS/s sampling rate
        sample_rate_hz = 500_000.0
        total_time_ms = (total_samples / sample_rate_hz) * 1000.0
        self.time_array = np.linspace(0, total_time_ms, total_samples)
        
        self.tabs.addTab(osc_tab, "Oscilloscope")
        
        self.update_y_range()
        self.update_timebase(self.timebase_slider.value())

    def setup_inspector_tab(self):
        ins_tab = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout(ins_tab)
        
        # Top banner for config (compact)
        banner_layout = QtWidgets.QHBoxLayout()
        banner_layout.setContentsMargins(6, 4, 6, 4)
        banner_layout.addWidget(QtWidgets.QLabel("RAM Limit (GB):"))
        
        self.ram_spin = QtWidgets.QDoubleSpinBox()
        self.ram_spin.setRange(0.1, 32.0)
        self.ram_spin.setValue(self.config.get("ram_limit_gb", 1.0))
        self.ram_spin.setSingleStep(0.5)
        banner_layout.addWidget(self.ram_spin)
        
        self.apply_btn = QtWidgets.QPushButton("Apply & Restart")
        self.apply_btn.clicked.connect(self.apply_ram_config)
        banner_layout.addWidget(self.apply_btn)
        
        self.clear_btn = QtWidgets.QPushButton("Clear Cache")
        self.clear_btn.clicked.connect(self.clear_cache)
        banner_layout.addWidget(self.clear_btn)
        
        banner_layout.addWidget(QtWidgets.QLabel(f"Pre-allocated: {self.max_packets:,} pkts"))
        banner_layout.addStretch()
        
        banner_widget = QtWidgets.QWidget()
        banner_widget.setObjectName("inspectorBanner")
        banner_widget.setStyleSheet("QWidget#inspectorBanner { background-color: #0d0d1a; border-bottom: 1px solid #1a2a4a; }")
        banner_widget.setLayout(banner_layout)
        main_layout.addWidget(banner_widget)
        
        # Splitter for Table and Detail View
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        
        # Left: Table (wrapped in a styled container)
        table_container = QtWidgets.QWidget()
        table_container.setObjectName("packetTableContainer")
        table_container.setStyleSheet("""
            #packetTableContainer {
                background: #0a0a14;
                border: 1px solid #1e1e3a;
                border-radius: 6px;
                padding: 4px;
            }
        """)
        table_vbox = QtWidgets.QVBoxLayout(table_container)
        table_vbox.setContentsMargins(4, 4, 4, 4)
        table_vbox.setSpacing(2)
        
        table_title = QtWidgets.QLabel("◈  PACKET LOG")
        table_title.setStyleSheet("color: #444; font-size: 10px; font-weight: bold; letter-spacing: 2px; padding: 2px 4px;")
        table_vbox.addWidget(table_title)
        
        self.packet_model = PacketTableModel(self)
        self.packet_table = QtWidgets.QTableView()
        self.packet_table.setModel(self.packet_model)
        self.packet_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.packet_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.packet_table.verticalHeader().setVisible(False)
        self.packet_table.clicked.connect(self.on_packet_selected)
        table_vbox.addWidget(self.packet_table)
        
        # Timer to refresh table without blocking UI
        self.table_timer = QtCore.QTimer()
        self.table_timer.timeout.connect(self.refresh_inspector)
        self.table_timer.start(1000) # Refresh table 1 time per second
        
        splitter.addWidget(table_container)
        
        # Right: Detail Panel with sub-tabs
        detail_tabs = QtWidgets.QTabWidget()
        detail_tabs.setStyleSheet("""
            QTabBar::tab { min-width: 80px; padding: 6px 16px; font-size: 12px; }
        """)

        # --- Sub-tab 1: Frame Data ---
        frame_tab = QtWidgets.QWidget()
        frame_layout = QtWidgets.QVBoxLayout(frame_tab)
        frame_layout.setContentsMargins(4, 4, 4, 4)

        self.detail_text = QtWidgets.QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setMaximumHeight(220)
        frame_layout.addWidget(self.detail_text)

        self.detail_plot = pg.PlotWidget(title="Packet Signal")
        self.detail_plot.showGrid(x=True, y=True, alpha=0.2)
        self.detail_plot.setYRange(0, ADC_MAX_VAL)
        self.detail_curve = self.detail_plot.plot(pen=pg.mkPen(color='#FF00FF', width=1.5))
        frame_layout.addWidget(self.detail_plot)

        detail_tabs.addTab(frame_tab, "Frame Data")

        # --- Sub-tab 2: Telemetry ---
        tel_tab = QtWidgets.QWidget()
        tel_layout = QtWidgets.QVBoxLayout(tel_tab)
        tel_layout.setContentsMargins(4, 4, 4, 4)

        self.tel_text = QtWidgets.QTextEdit()
        self.tel_text.setReadOnly(True)
        self.tel_text.setMaximumHeight(170)
        tel_layout.addWidget(self.tel_text)

        self.tel_bar_plot = pg.PlotWidget()
        self.tel_bar_plot.setBackground('#0d0d1a')
        self.tel_bar_plot.showGrid(x=False, y=True, alpha=0.15)
        self.tel_bar_plot.setMouseEnabled(x=False, y=False)
        self.tel_bar_plot.getAxis('bottom').setTicks([[
            (0, 'DMA'), (1, 'Metadata'), (2, 'Checksum'), (3, 'USB Tx')
        ]])
        self.tel_bar_plot.setLabel('left', 'Time', units='µs')
        self.tel_bar_items = []
        bar_colors = ['#FF9500', '#3DD6F5', '#BB86FC', '#FF4C4C']
        for i, color in enumerate(bar_colors):
            bar = pg.BarGraphItem(x=[i], height=[0], width=0.6,
                                  brush=color, pen=pg.mkPen(color, width=1))
            self.tel_bar_plot.addItem(bar)
            self.tel_bar_items.append(bar)
        tel_layout.addWidget(self.tel_bar_plot)

        detail_tabs.addTab(tel_tab, "Telemetry")
        detail_tabs.setCurrentIndex(1) # Telemetry is more important for analysis by default

        splitter.addWidget(detail_tabs)
        splitter.setSizes([400, 600])
        
        main_layout.addWidget(splitter)
        
        # Bottom: Memory Progress Bar
        self.memory_bar = QtWidgets.QProgressBar()
        self.memory_bar.setMinimum(0)
        self.memory_bar.setMaximum(self.max_packets)
        self.memory_bar.setValue(0)
        self.memory_bar.setFormat("Buffer Usage: 0 / %m Packets (0%)")
        
        main_layout.addWidget(self.memory_bar)
        
        self.tabs.addTab(ins_tab, "Packet Inspector")

    def apply_ram_config(self):
        self.config['ram_limit_gb'] = self.ram_spin.value()
        save_config(self.config)
        self.statusBar().showMessage("Restarting application...")
        # Cleanly stop hardware
        if self.data_source is not None:
            self.data_source.stop()
            self.data_source.wait()
        # Restart process
        os.execv(sys.executable, ['python'] + sys.argv)

    def _build_global_connection_bar(self):
        """Creates a persistent connection toolbar shown at the bottom of every tab."""
        conn_widget = QtWidgets.QWidget()
        conn_widget.setObjectName("globalConnBar")
        conn_widget.setStyleSheet("""
            QWidget#globalConnBar {
                background-color: #0a0a12;
                border-top: 1px solid #1a2a4a;
            }
        """)
        conn_layout = QtWidgets.QHBoxLayout(conn_widget)
        conn_layout.setContentsMargins(8, 4, 8, 4)
        conn_layout.setSpacing(8)

        port_label = QtWidgets.QLabel("COM Port:")
        port_label.setStyleSheet("color: #666; font-size: 13px;")
        conn_layout.addWidget(port_label)

        self.port_combo = QtWidgets.QComboBox()
        self.port_combo.setItemDelegate(QtWidgets.QStyledItemDelegate())
        self.port_combo.setMinimumWidth(240)
        self.refresh_ports()
        conn_layout.addWidget(self.port_combo)

        self.refresh_btn = QtWidgets.QPushButton("\u21BA  Refresh")
        self.refresh_btn.clicked.connect(self.refresh_ports)
        self.refresh_btn.setMinimumWidth(120)
        conn_layout.addWidget(self.refresh_btn)

        self.connect_btn = QtWidgets.QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.connect_btn.setMinimumWidth(130)
        conn_layout.addWidget(self.connect_btn)

        # Play / Stop button (disabled until connected)
        self.stream_btn = QtWidgets.QPushButton("\u25B6  Stream")
        self.stream_btn.setObjectName("streamBtn")
        self.stream_btn.clicked.connect(self.toggle_stream)
        self.stream_btn.setEnabled(False)
        self.stream_btn.setMinimumWidth(140)
        self.stream_btn.setStyleSheet("""
            QPushButton#streamBtn {
                background-color: #1a3a1a;
                color: #4CAF50;
                border: 1px solid #2d5a2d;
            }
            QPushButton#streamBtn:hover { background-color: #245024; }
            QPushButton#streamBtn:disabled { background-color: #1a1a1a; color: #444; border-color: #333; }
        """)
        conn_layout.addWidget(self.stream_btn)

        conn_layout.addStretch()

        # Status indicator on the right
        self.conn_status_dot = QtWidgets.QLabel("●")
        self.conn_status_dot.setStyleSheet("color: #333; font-size: 16px; padding-right: 2px;")
        self.conn_status_label = QtWidgets.QLabel("DISCONNECTED")
        self.conn_status_label.setStyleSheet("color: #555; font-size: 12px; font-family: monospace; letter-spacing: 1px;")
        conn_layout.addWidget(self.conn_status_dot)
        conn_layout.addWidget(self.conn_status_label)

        # Embed above the native status bar
        central = self.centralWidget()
        outer = QtWidgets.QWidget()
        outer_layout = QtWidgets.QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        outer_layout.addWidget(central)
        outer_layout.addWidget(conn_widget)
        self.setCentralWidget(outer)

    def clear_cache(self):
        """Resets the history buffer pointers, effectively emptying the packet log."""
        self.hist_head = 0
        self.hist_count = 0
        self.packet_model.layoutChanged.emit()
        self.detail_text.clear()
        self.detail_curve.setData([])
        self.memory_bar.setValue(0)
        self.refresh_inspector()

    def _auto_select_first_packet(self):
        """Automatically selects the 'Average' row in the inspector table."""
        if self.hist_count > 0:
            index = self.packet_model.index(0, 0)
            self.packet_table.setCurrentIndex(index)
            self.on_packet_selected(index)

    def format_bytes(self, num_bytes):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if num_bytes < 1024.0:
                return f"{num_bytes:.2f} {unit}"
            num_bytes /= 1024.0
        return f"{num_bytes:.2f} PB"

    def refresh_inspector(self):
        """Periodically refreshes the table and progress bar."""
        self.packet_model.layoutChanged.emit()
        self.memory_bar.setValue(self.hist_count)
        
        bytes_per_packet = (SAMPLES_PER_BUFFER * 2) + 4 + 4 + 1 + 2
        used_bytes = self.hist_count * bytes_per_packet
        total_bytes = self.max_packets * bytes_per_packet
        
        pct = (self.hist_count / max(1, self.max_packets)) * 100
        
        fmt = f"Buffer Usage: {self.hist_count:,} / {self.max_packets:,} Packets "
        fmt += f"({self.format_bytes(used_bytes)} / {self.format_bytes(total_bytes)})  -  {pct:.1f}%"
        self.memory_bar.setFormat(fmt)

    def clear_oscilloscope(self):
        """Clears the live oscilloscope display buffer."""
        self.display_buffer.fill(2048) # 2048 is the center for 12-bit ADC
        v_max = self.voltage_spin.value()
        voltage_data = (self.display_buffer / ADC_MAX_VAL) * v_max
        self.curve.setData(self.time_array, voltage_data)

    def on_packet_selected(self, index):
        if not index.isValid(): return
        
        row = index.row()
        is_avg = (row == 0)

        if is_avg:
            # --- Special: Calculate Averages ---
            count = max(1, self.hist_count)
            # Use only valid parts of buffers
            t_dma = int(np.mean(self.hist_tel_dma[:count]))
            t_meta = int(np.mean(self.hist_tel_meta[:count]))
            t_chk = int(np.mean(self.hist_tel_chk[:count]))
            t_usb = int(np.mean(self.hist_tel_usb[:count]))
            t_loop = int(np.mean(self.hist_tel_loop[:count]))
            
            seq = "ALL HISTORY"
            time_us = 0
            flags = 0
            crc = 0
            samples = np.zeros(SAMPLES_PER_BUFFER)
            banner_title = "▶ HISTORY AVERAGE DATA"
            banner_color = "#3D8EFF"
            banner_border = "#1e3a5f"
        else:
            # --- Normal: Packet Data ---
            row_idx = row - 1
            if self.hist_count < self.max_packets:
                phys_idx = row_idx
            else:
                phys_idx = (self.hist_head + row_idx) % self.max_packets
                
            seq = self.hist_seq[phys_idx]
            time_us = self.hist_time[phys_idx]
            flags = self.hist_flags[phys_idx]
            crc = self.hist_crc[phys_idx]
            samples = self.hist_samples[phys_idx]
            t_dma = int(self.hist_tel_dma[phys_idx])
            t_meta = int(self.hist_tel_meta[phys_idx])
            t_chk = int(self.hist_tel_chk[phys_idx])
            t_usb = int(self.hist_tel_usb[phys_idx])
            t_loop = int(self.hist_tel_loop[phys_idx])
            banner_title = "▶ FRAME DATA"
            banner_color = "#3D8EFF"
            banner_border = "#1e3a5f"
        
        # --- Tab 1: Frame Data ---
        frame_html = f"""
        <div style="font-family: monospace; font-size: 13px; background:#0d0d1a; border:1px solid #222; border-radius:6px; padding:8px; margin:2px;">
            <div style="color:{banner_color}; font-size:11px; font-weight:bold; letter-spacing:1px; margin-bottom:6px; padding-bottom:4px; border-bottom:1px solid {banner_border};">{banner_title}</div>
            <table width="100%" cellpadding="4" cellspacing="0">
                <tr>
                    <td style="color:#666; width:35%;">{"Packet Range" if is_avg else "Sequence ID"}</td>
                    <td style="color:#39FF14; font-size:15px;"><b>{seq}</b></td>
                </tr>
                <tr>
                    <td style="color:#666;">{"Avg. Interval" if is_avg else "Timestamp"}</td>
                    <td style="color:#39FF14;">{time_us:,} µs</td>
                </tr>
                <tr>
                    <td style="color:#666;">Flags</td>
                    <td style="color:#39FF14;">0x{flags:02X}</td>
                </tr>
                <tr>
                    <td style="color:#666;">CRC</td>
                    <td style="color:#39FF14;">0x{crc:04X}</td>
                </tr>
                <tr>
                    <td style="color:#666;">Total Points</td>
                    <td style="color:#888;">{"N/A" if is_avg else f"{len(samples):,}"}</td>
                </tr>
            </table>
        </div>
        """
        self.detail_text.setHtml(frame_html)
        if is_avg:
            self.detail_curve.setData([]) # Clear curve for average view
        else:
            self.detail_curve.setData(samples)

        # --- Tab 2: Telemetry ---
        if t_loop == 0:
            tel_html = f"""
            <div style="font-family: monospace; font-size: 13px; background:#0d0d1a; border:1px solid #222; border-radius:6px; padding:20px; margin:2px; text-align:center;">
                <div style="color:#555; font-size:18px; font-weight:bold; letter-spacing:2px; margin-bottom:10px;">◈ NO TELEMETRY DATA</div>
                <div style="color:#444; font-size:12px;">The connected hardware is not sending timing metrics for this frame.</div>
            </div>
            """
        else:
            tel_html = f"""
            <div style="font-family: monospace; font-size: 13px; background:#0d0d1a; border:1px solid #222; border-radius:6px; padding:8px; margin:2px;">
                <div style="color:#72C748; font-size:11px; font-weight:bold; letter-spacing:1px; margin-bottom:6px; padding-bottom:4px; border-bottom:1px solid #2a4a1e;">{"▶ AVERAGE TELEMETRY" if is_avg else f"▶ TELEMETRY  <span style='color:#555; font-size:10px; font-weight:normal;'>Seq #{seq}</span>"}</div>
                <table width="100%" cellpadding="4" cellspacing="0">
                    <tr>
                        <td style="color:#666; width:35%;">DMA Transfer</td>
                        <td style="color:#FF9500;"><b>{t_dma:,} µs</b></td>
                        <td style="color:#555; font-size:11px;">{t_dma/max(1,t_loop)*100:.1f}% of loop</td>
                    </tr>
                    <tr>
                        <td style="color:#666;">Metadata Fill</td>
                        <td style="color:#3DD6F5;"><b>{t_meta:,} µs</b></td>
                        <td style="color:#555; font-size:11px;">{t_meta/max(1,t_loop)*100:.1f}%</td>
                    </tr>
                    <tr>
                        <td style="color:#666;">Checksum Calc</td>
                        <td style="color:#BB86FC;"><b>{t_chk:,} µs</b></td>
                        <td style="color:#555; font-size:11px;">{t_chk/max(1,t_loop)*100:.1f}%</td>
                    </tr>
                    <tr>
                        <td style="color:#666;">USB Transport</td>
                        <td style="color:#FF4C4C;"><b>{t_usb:,} µs</b></td>
                        <td style="color:#555; font-size:11px;">{t_usb/max(1,t_loop)*100:.1f}%</td>
                    </tr>
                    <tr style="border-top:1px solid #222; margin-top:4px;">
                        <td style="color:#888;">Total Loop</td>
                        <td style="color:#39FF14;"><b>{t_loop:,} µs</b></td>
                        <td style="color:#555; font-size:11px;">{t_loop/1000:.2f} ms &nbsp;|&nbsp; {1e6/max(1,t_loop):.1f} FPS</td>
                    </tr>
                </table>
            </div>
            """
        self.tel_text.setHtml(tel_html)

        # Update bar chart
        heights = [t_dma, t_meta, t_chk, t_usb]
        for bar_item, h in zip(self.tel_bar_items, heights):
            bar_item.setOpts(height=h)

    def update_timebase(self, value):
        """Updates the X-axis range to zoom into the latest samples on the right side of the screen."""
        total_samples = SAMPLES_PER_BUFFER * DISPLAY_CHUNKS
        sample_rate_hz = 500_000.0
        total_time_ms = (total_samples / sample_rate_hz) * 1000.0
        
        # Convert the zoom 'value' (which is in samples) to time in ms
        view_time_ms = (value / sample_rate_hz) * 1000.0
        
        # Zoom into the newest data at the end of the buffer
        self.plot_widget.setXRange(total_time_ms - view_time_ms, total_time_ms, padding=0)

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

    def _set_conn_status(self, state):
        """Updates the status indicator. state: 'disconnected', 'connected', 'streaming'"""
        styles = {
            'disconnected': ('color: #444; font-size: 16px;', 'color: #555; font-size: 12px; font-family: monospace; letter-spacing: 1px;', '●', 'DISCONNECTED'),
            'connected':    ('color: #FF9500; font-size: 16px;', 'color: #FF9500; font-size: 12px; font-family: monospace; letter-spacing: 1px;', '●', 'CONNECTED — IDLE'),
            'streaming':    ('color: #39FF14; font-size: 16px;', 'color: #39FF14; font-size: 12px; font-family: monospace; letter-spacing: 1px;', '●', 'STREAMING'),
        }
        dot_style, lbl_style, dot_char, lbl_text = styles.get(state, styles['disconnected'])
        self.conn_status_dot.setStyleSheet(dot_style)
        self.conn_status_dot.setText(dot_char)
        self.conn_status_label.setStyleSheet(lbl_style)
        self.conn_status_label.setText(lbl_text)

    def toggle_connection(self):
        """Opens or closes the serial port connection (does NOT start streaming)."""
        if self.data_source is not None and self.data_source.isRunning():
            # Disconnect
            self.data_source.stop()
            self.data_source.wait()
            self.data_source = None
            self.connect_btn.setText("Connect")
            self.port_combo.setEnabled(True)
            self.refresh_btn.setEnabled(True)
            self.stream_btn.setEnabled(False)
            self.stream_btn.setText("\u25B6  Stream")
            self.stream_btn.setStyleSheet("""
                QPushButton#streamBtn {
                    background-color: #1a3a1a; color: #4CAF50; border: 1px solid #2d5a2d;
                }
                QPushButton#streamBtn:disabled { background-color: #1a1a1a; color: #444; border-color: #333; }
            """)
            self._set_conn_status('disconnected')
        else:
            if self.port_combo.count() == 0:
                return
            port = self.port_combo.currentData()
            self.data_source = SerialPicoSource()
            self.data_source.port = port
            self.data_source.streaming = False   # Start in idle mode
            self.data_source.new_data_signal.connect(self.update_plot)
            self.data_source.error_signal.connect(self.handle_source_error)
            self.data_source.start()
            self.connect_btn.setText("Disconnect")
            self.port_combo.setEnabled(False)
            self.refresh_btn.setEnabled(False)
            self.stream_btn.setEnabled(True)
            self._set_conn_status('connected')

    def toggle_stream(self):
        """Starts or pauses data streaming on an already-open connection."""
        if self.data_source is None:
            return
        if self.data_source.streaming:
            # Pause
            self.data_source.streaming = False
            self.stream_btn.setText("\u25B6  Stream")
            self.stream_btn.setStyleSheet("""
                QPushButton#streamBtn {
                    background-color: #1a3a1a; color: #4CAF50; border: 1px solid #2d5a2d;
                }
                QPushButton#streamBtn:hover { background-color: #245024; }
                QPushButton#streamBtn:disabled { background-color: #1a1a1a; color: #444; }
            """)
            self._set_conn_status('connected')
        else:
            # Play
            self.data_source.streaming = True
            self.stream_btn.setText("\u23F9  Stop")
            self.stream_btn.setStyleSheet("""
                QPushButton#streamBtn {
                    background-color: #3a1a1a; color: #FF4C4C; border: 1px solid #5a2d2d;
                }
                QPushButton#streamBtn:hover { background-color: #502424; }
                QPushButton#streamBtn:disabled { background-color: #1a1a1a; color: #444; }
            """)
            self._set_conn_status('streaming')

    def handle_source_error(self, err_msg):
        """Handles connection drops or port setup failures."""
        if self.data_source is not None:
            self.data_source.stop()
            self.data_source.wait()
            self.data_source = None
        self.connect_btn.setText("Connect")
        self.port_combo.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.stream_btn.setEnabled(False)
        self.stream_btn.setText("\u25B6  Stream")
        self._set_conn_status('disconnected')
        QtWidgets.QMessageBox.critical(self, "Connection Error", f"Lost connection or failed to configure port:\n{err_msg}")

    def start_simulation(self):
        """Starts the mock source for testing without hardware"""
        self.data_source = MockPicoSource()
        self.data_source.new_data_signal.connect(self.update_plot)
        self.data_source.start()
        self._set_conn_status('streaming')

    def update_plot(self, packet):
        """Immediately renders the new hardware frame to screen for zero-latency plotting."""
        # --- 1. Save to History Buffer ---
        h = self.hist_head
        self.hist_seq[h] = packet['seq']
        self.hist_time[h] = packet['time']
        self.hist_flags[h] = packet['flags']
        self.hist_crc[h] = packet['crc']
        self.hist_samples[h] = packet['samples']
        
        tel = packet['telemetry']
        self.hist_tel_dma[h] = tel['dma_us']
        self.hist_tel_meta[h] = tel['metadata_us']
        self.hist_tel_chk[h] = tel['checksum_us']
        self.hist_tel_usb[h] = tel['usb_transport_us']
        self.hist_tel_loop[h] = tel['total_loop_us']
        
        self.hist_head = (self.hist_head + 1) % self.max_packets
        if self.hist_count < self.max_packets:
            self.hist_count += 1

        # Auto-select first packet in inspector if it's the first one
        if self.hist_count == 1:
            QtCore.QTimer.singleShot(0, self._auto_select_first_packet)


        # --- 2. Update Oscilloscope Display ---
        new_samples = packet['samples']
        # Shift the display buffer to the left and append the new 1024 samples
        self.display_buffer = np.roll(self.display_buffer, -SAMPLES_PER_BUFFER)
        self.display_buffer[-SAMPLES_PER_BUFFER:] = new_samples
        
        # Convert raw ADC values to Voltage
        v_max = self.voltage_spin.value()
        voltage_data = (self.display_buffer / ADC_MAX_VAL) * v_max
        
        # Update curve data in the UI
        self.curve.setData(self.time_array, voltage_data)

    def closeEvent(self, event):
        """Ensure clean thread shutdown when closing the window"""
        if self.data_source is not None:
            self.data_source.stop()
            self.data_source.wait()
        event.accept()

if __name__ == "__main__":
    import ctypes
    # Tell Windows to treat this process as a standalone app, so it gets its own taskbar icon
    myappid = 'casasola.oscipi.oscilloscope.1'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QtWidgets.QApplication(sys.argv)
    
    # Dark Mode style for the app
    app.setStyle("Fusion")
    
    win = OscilloscopeUI()
    win.show()
    sys.exit(app.exec_())