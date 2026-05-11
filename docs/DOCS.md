# Engineering & Architecture Notes

This document provides deep technical details, architectural decisions, and lab experiment measurements for each milestone of the Oscipi project.

---

## Hardware Architecture Evolution

### v0.1: Manual CPU Sampling
- **Context:** Initial proof of concept loop using `sleep_ms(1)` in software.
- **Data & Observations:** Real throughput was 0.8 FPS instead of the expected 1.0 FPS. Generating 1024 samples took ~1250ms.
- **Discovery:** Software timing is non-deterministic. CPU overhead and USB buffering added ~250ms of delay per frame. This approach resulted in high jitter and severe "phase jumps" in the signal.
- **Resolution:** Required moving all strict timing responsibilities to hardware peripherals (Timer and DMA).

### v0.2: DMA (Single Buffer)
- **Context:** DMA hardware-paced sampling driven by DREQ, featuring a custom Telemetry instrumentation envelope.
- **Hypothesis (USB CDC Transport Bottleneck):** USB ACK latency is actively blocking the main execution loop.
- **Measurements:**
  - DMA Sampling time: 2,048 µs
  - Checksum calculation: 15 µs
  - USB Write/Flush overhead: 185,000 µs
- **Conclusion:** Single buffering is entirely ineffective for high-speed streaming. The DMA hardware had to be halted during USB transmission, resulting in 99% idle time and massive gaps in the signal continuity.

### v0.3: DMA (Double Buffering)
- **Design Challenge:** Eliminate the massive USB write gap discovered in v0.2.
- **Architecture:** Implemented a Ping-Pong buffer system. Buffer A is filled by the DMA asynchronously while the CPU computes checksums and flushes Buffer B over USB.
- **Mechanism:** Cross-triggering DMA channels handle the buffer swapping automatically at the hardware level.
- **Scalability Issues:** Managing complex hardware states and synchronization flags in bare-metal C leads to brittle code when attempting to add more features.

### v0.4: ADC Streaming
- **Design Challenge:** Transition from synthetic data to real physical signals.
- **Architecture:** Replaced the synthetic software sine wave generator with direct RP2040 internal ADC sampling.
- **Implementation:** The ADC captures data and feeds it directly to the DMA channels with a paced Timer, ensuring high-speed streaming without jitter and no signal gaps.

### v0.5: RTOS Multi-Tasking
- **Design Challenge:** Managing ADC, DMA, and USB concurrently became too complex for a single sequential super-loop.
- **Architecture:** Complete transition to FreeRTOS.
- **Mechanism:** 
  - Uses preemptive scheduling with dedicated task priorities (e.g., high priority for DMA/ADC management, lower priority for USB transport).
  - Implements thread-safe primitives like Task Notifications and Semaphores to safely hand over buffer ownership between the hardware interrupt routines and the application software logic.

### v0.6: Command Console
- **Design Challenge:** The device was purely passive, constantly streaming data without the ability to be configured by the host.
- **Architecture:** Implementation of a bi-directional protocol over USB.
- **Mechanism:** Added a dedicated parsing task to receive and execute control packets from the GUI. This enables on-the-fly configuration of sampling rates, triggers, and active channels without requiring a hardware reset.

---

## Software Interface Evolution

### Minor v0.1.1: Python/Qt Interface Architecture
- **Context:** Initial development of the desktop companion software (`gui.py` and `hw_emulator.py`) using PyQt5 and pyqtgraph.
- **Challenge 1 (Performance & Memory):** The default `QTableWidget` and Python native lists completely crashed the UI when attempting to load hundreds of thousands of data packets for the Packet Inspector.
- **Solution 1 (Pre-allocated Circular Buffers):** Migrated to massive Numpy pre-allocated arrays based on a user-defined RAM limit (e.g., 1GB = ~500,000 packets). This guarantees zero garbage collection spikes and strict, predictable RAM boundaries. The memory is managed as an infinite circular buffer.
- **Solution 2 (Model-View Separation):** Injected the Numpy arrays directly into a custom, highly-optimized `QAbstractTableModel`. This completely decouples the UI rendering from the massive data model. The UI only requests data for the rows physically visible on the screen, allowing instant, zero-latency scrolling through gigabytes of data.
- **Challenge 2 (Windows Rendering Artifacts):** Native Windows rendering injected white lines and inconsistent borders into dark-themed dropdown menus (`QComboBox`), breaking the aesthetic.
- **Solution 2 (Styled Delegates):** Forced PyQt to abandon the native OS rendering by applying `setItemDelegate(QtWidgets.QStyledItemDelegate())` to comboboxes, giving full control back to the custom CSS styling engine.
- **Outcome:** A completely stable, 60 FPS real-time oscilloscope that can pre-allocate gigabytes of RAM for packet history without freezing. It ensures 0 dropped frames during analysis, handles UART connection drops gracefully via custom PyQt signals, and maintains a fully customized professional "Dark/Neon" aesthetic.
