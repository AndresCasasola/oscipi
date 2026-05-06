# Pico-OS Project Evolution

This document tracks the different versions and architectural milestones of the oscilloscope project.

## v0.1: Bare-Metal (No DMA)
- **Status**: Completed.
- **Description**: The MCU calculates a sine wave and manually copies it to the transmission buffer using the CPU in a `for` loop.
- **Limitations**: High CPU usage. The CPU is blocked generating and copying samples, which limits the transmission rate and wastes CPU cycles that could be used for other tasks.

## v0.2: Bare-Metal with DMA (Single Buffer)
- **Status**: Next to implement.
- **Description**: The sine wave is pre-calculated and stored in a fixed array. A DMA data channel continuously copies the signal to the USB transmission buffer, paced by a DMA timer (DREQ). A DMA control channel is used to chain the transfer, creating an infinite loop. The CPU is completely freed from moving samples and only generates the checksum and USB packets.
- **Limitations**: Since there is only one buffer, the DMA might overwrite the data while the CPU is transmitting it over USB, causing tearing or race conditions.

## v0.3: Bare-Metal with DMA (Double Buffering / Ping-Pong)
- **Status**: Planned.
- **Description**: Introduces a double-buffer system (Ping-Pong). The DMA fills one buffer while the CPU transmits the other. This completely eliminates tearing and race conditions, ensuring perfect data integrity without dropping samples.

## v0.4: RTOS Integration
- **Status**: Planned.
- **Description**: The system will be migrated to FreeRTOS. Tasks will be created for USB communication, DMA management, and other system functions. This provides maximum efficiency, modularity, and deterministic behavior.

## v0.5+: Command Console & UI Configuration
- **Status**: Planned.
- **Description**: Implementation of a bidirectional communication protocol. The Python/Qt UI will be able to send commands to the firmware to configure oscilloscope parameters (e.g., sampling rate, trigger levels, channel selection) in real-time.
