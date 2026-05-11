# Oscipi Hardware Emulator

The `hw_emulator.py` script is a standalone tool designed to simulate the Raspberry Pi Pico oscilloscope hardware. It allows you to test the PC-side graphical interface and serial parsing logic without needing the physical microcontroller connected.

## Overview

The emulator accurately replicates the firmware's data transmission layer. It:
1. Generates a noisy sine wave to simulate ADC input.
2. Structures the data into the exact packets expected by the GUI (including metadata like Sequence ID and Timestamps).
3. Computes the identical CRC checksum used by the hardware.
4. Transmits the raw binary frames over a COM port at `921600` baud.

## Requirements

No external dependencies or virtual serial ports are needed! The emulator now supports internal TCP routing.

## How to Use

1. **Start the Emulator:** Run the emulator script and set it to host a TCP socket.
   ```bash
   python python/hw_emulator.py tcp:5555
   ```
3. **Optional Arguments:**
   - `--fps`: Adjust the transmission rate (default is 50.0 frames per second).
     ```bash
     python hw_emulator.py COM3 --fps 30
     ```

## Connecting the GUI

Once the emulator is running on `COM3`, open your `gui.py` application.
1. Make sure `SIMULATE_MODE` is set to `False` in the GUI source code so it enables serial connections.
2. Select the *other* half of your virtual pair (e.g., `COM4`) from the COM Port dropdown.
3. Click **Connect**. 

You should immediately see the simulated sine wave streaming into the application, validating that the PC software can correctly handle framing, decoding, and checksum verifications.

## Frame Structure

For reference, the emulator constructs frames exactly like the C firmware:
- **Sync Word:** `0xAA 0x55` (2 bytes)
- **Metadata:** Sequence ID (4 bytes), Timestamp (4 bytes), Flags (1 byte), Padding (1 byte)
- **Payload:** 1024 12-bit ADC samples padded to 16-bit integers (2048 bytes)
- **Checksum:** CRC16 calculated over the metadata and payload (2 bytes)
