# Pico-OS Graphical User Interface

The GUI is a PyQt5-based application designed to visualize high-speed ADC data streamed from the Raspberry Pi Pico oscilloscope firmware (or the hardware emulator). 

## Overview

The application features a dark-themed, high-performance plotting interface built with `pyqtgraph`. It is designed to smoothly render large buffers of ADC samples while validating data integrity in real-time.

### Key Features
- **Real-Time Rendering:** Utilizes an animation queue to smoothly push buffered hardware frames to the screen at ~60 FPS, providing a classic oscilloscope "persistence" feel.
- **Serial Driver Layer:** Validates sync bytes, sequence IDs, and hardware-calculated CRCs to ensure no corrupted frames are displayed.
- **Throughput Monitoring:** Prints real-time FPS and KB/s throughput metrics to the terminal.
- **Internal Simulation:** Features an offline `SIMULATE_MODE` for testing the UI layout without any serial connections.

## Requirements

Ensure you have the necessary Python dependencies installed:
```bash
pip install numpy pyserial pyqt5 pyqtgraph
```

## Configuration

At the top of the GUI script, there is a global configuration block:
```python
# --- GLOBAL BUNKER CONFIGURATION ---
SIMULATE_MODE = False  # Change to True to test UI without serial
BAUDRATE = 921600      # Must match the Pico firmware
SAMPLES_PER_BUFFER = 1024
DISPLAY_CHUNKS = 5     # Number of consecutive buffers to show on screen
```

## How to Use

1. **Run the Application:**
   ```bash
   python gui.py
   ```
2. **Select Device:** Once the window opens, select your Pico's COM port (or the virtual COM port if using the emulator) from the top dropdown menu. You can use the `Refresh Ports` button if you plugged the device in after launching the app.
3. **Connect:** Click the **Connect** button. The application will initialize the serial stream, wait for the `0xAA 0x55` sync bytes, and begin rendering the signal.
4. **Disconnect:** Click **Disconnect** to safely close the serial port and halt the data stream.

## Architecture

The software is split into two primary layers:
1. **Data Layer (`DataSource` classes):** Runs on a separate `QThread` to prevent blocking the UI. `SerialPicoSource` handles the raw UART reading and data unpacking, while `MockPicoSource` generates offline dummy data. Both emit a `new_data_signal` when a valid frame is ready.
2. **Graphical Layer (`OscilloscopeUI`):** Handles the window layout, catches the data signals, and queues them into a rolling buffer that is painted to the screen by a high-frequency `QTimer`.
