# Oscipi Docs

This document provides deep technical details, architectural decisions, and lab experiment measurements for each milestone of the Oscipi project.

## v0.2 - DMA (Single Buffer)

The v0.2 milestone represents the transition from software-timed loops to hardware-deterministic sampling. The goal was to establish a high-speed data pipe (~500 kHz) and instrument it to identify system bottlenecks.

### 1. Hardware Architecture

At the core of v0.2 is the **RP2040 DMA Engine**, configured to generate data independently of the CPU.

*   **Paced DMA Transfer:** A dedicated DMA Timer is claimed and configured as a Data Request (DREQ) signal. By setting the fraction to 1/250 (at 125 MHz system clock), we achieve a strictly deterministic sampling rate of **500 kHz**.
*   **DMA Chaining (Infinite Loop):** To simulate a continuous signal, two DMA channels are chained:
    1.  **Data Channel:** Copies 1024 samples from a pre-calculated Sine table (RAM) to the active transfer buffer.
    2.  **Control Channel:** When the Data Channel finishes, it triggers the Control Channel, which resets the Data Channel's `read_addr` back to the start of the Sine table.
*   **Deterministic Timing:** Unlike `sleep_us()`, the DMA-DREQ mechanism is immune to CPU interrupts or code execution jitters, ensuring a stable "timebase" for the oscilloscope.

### 2. Protocol & Data Framing

To enable deep analysis in the Packet Inspector, a structured binary protocol was implemented:

| Size (Bytes) | Field | Description |
|---|---|---|
| 2 | **Header** | `0xAA 0x55` for frame synchronization. |
| 20 | **Telemetry Envelope** | 5x `uint32_t` measuring µs for: DMA wait, Metadata, Checksum, USB Tx, and Total Loop. |
| 4 | **Sequence ID** | Monotonically increasing counter to detect dropped frames. |
| 4 | **Timestamp** | MCU uptime in microseconds when the frame was processed. |
| 2 | **Flags** | Status bits (padding/future use). |
| 2048 | **Samples** | 1024 samples of 16-bit data (raw ADC values). |
| 2 | **Checksum** | 16-bit XOR result of metadata and samples. |

### 3. Granular Telemetry Strategy

One of the most critical features of v0.2 is the **Micro-Phase Instrumentation**. By wrapping each logic block in `time_us_32()` calls, the firmware reports its internal state back to the GUI:

```c
// Example of instrumentation loop
t_frame.total_loop_us = time_us_32() - t_start_loop;
t_start_loop = time_us_32();

dma_channel_wait_for_finish_blocking(chan_data); // Wait for HW
t_frame.dma_us = time_us_32() - t_dma_start;

// ... calculate checksum and metadata ...

fwrite(header, 1, HEADER_SIZE, stdout);
fflush(stdout); // Blocking USB transport
t_frame.usb_transport_us = time_us_32() - t_usb_start;
```

### 4. Results & Design Identification

The telemetry data extracted in this version led to a breakthrough in understanding the RP2040's limitations:

1.  **The USB CDC Wall:** USB transport accounts for **~99%** of the loop cycle time. While DMA takes ~2ms to fill a buffer, `fflush(stdout)` takes ~180-200ms depending on the host acknowledgement.
2.  **Temporal Blindness:** In this single-buffer design, the DMA must be restarted *after* the USB transfer is complete. This means the system is "blind" (not sampling) during 99% of its uptime.
3.  **Need for Double Buffering:** The v0.2 measurements proved that high-fidelity streaming requires a "Ping-Pong" architecture where the DMA fills Buffer B while the CPU handles the slow USB transport of Buffer A.

> [!IMPORTANT]
> This version validated that the RP2040 hardware (DMA/Timer) is capable of 500 kHz sampling with 0 jitter, but the software architecture must evolve to hide the USB latency.
