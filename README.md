# Oscipi: Raspberry Pi Pico Oscilloscope

[![Pico OS CI](https://github.com/AndresCasasola/oscipi/actions/workflows/pico_ci.yml/badge.svg)](https://github.com/AndresCasasola/oscipi/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform: Raspberry Pi Pico](https://img.shields.io/badge/Platform-Raspberry_Pi_Pico-blueviolet)](https://www.raspberrypi.com/documentation/microcontrollers/raspberry-pi-pico.html)

**Oscipi** is a digital oscilloscope powered by the RP2040. It features a robust C firmware backed by a real-time Python user interface.

---

## 1. Features

* **Real-Time Visualization:** High-performance GUI using `PyQtGraph` for low-latency signal rendering.
* **Test-Driven Development:** Firmware logic validated via `Unity` unit testing framework.
* **Automated CI/CD:** GitHub Actions pipeline for automated testing and firmware compilation (`.uf2`).
* **Cross-Platform:** One-click launchers for Windows and Linux environments.

## 2. Repository Structure

```text
.
├── .github/            # CI/CD Workflows (GitHub Actions)
├── gui/                # Desktop Application (Python + PyQtGraph)
│   └── main_ui.py      # Main Entry point for the GUI
├── src/                # Firmware Source Code (C / Pico SDK)
├── test/               # Unit Tests (C / Unity Framework)
├── unity/              # Unity Test Library source
├── .gitignore          # Version control exclusion rules
├── CMakeLists.txt      # Build configuration for Raspberry Pi Pico
├── requirements.txt    # Python package dependencies
├── run_gui.bat         # One-click launcher (Windows)
└── run_gui.sh          # One-click launcher (Linux/macOS)
```

## 3. Getting Started (Firmware)
### Prerequisites:
- Pico SDK v2.2.0+
- ARM GCC Toolchain
- Ninja (Recommended) or Make.
- picotool (Essential for a smooth workflow).

### Compilation
From the project root:
```powershell
# 1. Create and enter build directory
# Pro tip: If you want a clean rebuild, delete everything inside 'build' first:
# Remove-Item -Recurse -Force * (Execute from build directory)
cd build
# 2. Configure project
cmake .. -G Ninja
# 3. Build firmware
cmake --build .
```

### Flashing the Pico
You can use the picotool utility to flash without touching the hardware:
``` PowerShell
# 1. Force the Pico into BOOTSEL mode via USB
picotool reboot -f -u
# 2. Upload and execute the binary
picotool load -x app.uf2
```

Note: If picotool is not available, hold the BOOTSEL button while connecting the Pico and drag the .uf2 file into the RPI-RP2 drive.

## 4. System Architecture

The project is split into two main domains: the **Real-Time Firmware** (RP2040) and the **High-Level UI** (Python).

```mermaid
graph LR
    subgraph DESKTOP ["Desktop PC - Python"]
        direction LR
        TH1("<b>Thread: Serial Reader</b><br/>High-frequency polling of the serial<br/>port. No blocking of the UI.")
        TH2("<b>Thread: UI Controller</b><br/>Main thread. Handles window events<br/>and user interaction.")
        TH3("<b>Thread: Graph Renderer</b><br/>Handles PyQtGraph calculations and<br/>GPU-accelerated plotting.")
        
        TH1 --- TH2 --- TH3
    end
    subgraph RP2040 ["RP2040 - FreeRTOS"]
        direction LR
        T1("<b>Task: Sampling (Priority 3)</b><br/>Direct hardware control. Manages ADC<br/>and DMA interrupts.")
        T2("<b>Task: Processing (Priority 2)</b><br/>Heavy lifting. Digital filtering, RMS,<br/>and Edge AI inference.")
        T3("<b>Task: Comm (Priority 1)</b><br/>Lowest priority. Handles the UART<br/>hardware buffer and Protocol encoding.")
        
        T1 --- T2 --- T3
    end
```

```mermaid
graph TD
    %% Physical World
    P1((Analog Signal)) ==>|Voltage| HW[ADC Hardware]

    %% Firmware Path
    subgraph FW ["Firmware Data Path"]
        direction LR
        HW -.->|DMA Transfer| B1[(Raw Buffer)]
        B1 -->|Digital Filtering| B2[(Processed Data)]
        B2 -->|Packet Serialization| UART[UART TX]
    end

    %% Communication
    UART ==>|Binary Protocol| PC_RX[Serial Port]

    %% Software Path
    subgraph SW ["Software Data Path"]
        direction LR
        PC_RX -->|Byte Stream| PARSER[Protocol Parser]
        PARSER -->|NumPy Array| BUFFER[(Display Buffer)]
        BUFFER -->|Vectorized Plotting| GPU[PyQtGraph/GPU]
    end

    %% Visualization
    GPU ==>|Pixel Data| SCREEN[Monitor View]

    %% Control Path (Feedback)
    SCREEN -.->|User Input| CMD[Command Generator]
    CMD -.->|Control Packets| PC_RX
    PC_RX -.->|Trigger/Scale Config| T_PROC[Processing Task]
```

## 5. Threading & Communication

To ensure a smooth user experience without "freezing" the interface, the application implements a **Producer-Consumer** pattern:

1.  **Firmware Side (The Producer):**
    * **Core 0:** Handles the main oscilloscope logic and ADC sampling at a fixed frequency.
    * **UART:** Samples are packed into a custom binary protocol to maximize throughput over the serial port.

2.  **Software Side (The Consumer):**
    * **Serial Thread:** A dedicated background thread continuously listens to the COM port. This prevents the GUI from lagging while waiting for data.
    * **Queue Management:** Data is passed to the UI using a thread-safe buffer.
    * **UI Thread (PyQtGraph):** Every 20ms, the UI "wakes up," grabs the latest batch of samples from the buffer, and updates the plot using vectorized NumPy operations.

## 6. Development Tips
### Quality of Life (Linux)
Many Linux distros don't come with the venv module installed by default. If you encounter errors creating the environment, run:

```Bash
sudo apt install python3-venv
```

### FreeRTOS Insight
The kernel is configured to handle the RP2040's architecture with specific mapping for `isr_svcall`, `isr_pendsv`, and `isr_systick` to ensure the RTOS scheduler takes control of the hardware interrupts.