# Engineering Lab Notes

## Exp 01: Manual Sampling vs Timing Overhead
- **Context:** v0.1 loop using `sleep_ms(1)`.
- **Observation:** Real throughput was 0.8 FPS instead of 1.0 FPS.
- **Data:** 1024 samples took ~1250ms.
- **Discovery:** CPU overhead and USB buffering added ~250ms of delay.
- **Action:** Moved to Hardware DMA (v0.2).

## Exp 02: USB CDC Transport Bottleneck
- **Context:** v0.2 with Telemetry instrumentation.
- **Hypothesis:** USB ACK latency is blocking the main loop.
- **Measurements:** - DMA: 2,048 us
  - Checksum: 15 us
  - USB Write/Flush: 185,000 us
- **Conclusion:** Single buffering is ineffective for high-speed streaming due to the 99% idle time during USB transmission.