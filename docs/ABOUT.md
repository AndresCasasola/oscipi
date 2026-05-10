# Oscipi

**Oscipi** is an application designed to transform a Raspberry Pi Pico into a **professional digital oscilloscope**. It is the ideal tool for engineers, makers, and students who need to visualize electrical signals in real-time with a level of precision and fluidity that entry-level solutions simply cannot provide.

## What is Oscipi?

At its core, it is a high-speed "listening" system. While a multimeter gives you a static number (e.g., 3.3V), **Oscipi** allows you to see the "movie" of that electricity: how it rises, how it falls, whether it has noise, or if it is behaving as it should.

What makes Oscipi unique is its **hardened architecture**. It has been designed so the hardware works autonomously, ensuring that not a single detail of the signal is lost—even when the computer is busy processing the data.

## What is it for?

* **Circuit Debugging:** Find out why a sensor isn't working or if a communication signal has interference.
* **Electronics Learning:** Visualize sine, square, and PWM waves to understand how theory works in real life.
* **Signal Analysis:** Measure exact timings, frequencies, and voltages with an intuitive visual interface on your computer.
* **Low-Cost Prototyping:** Gain professional visualization capabilities using hardware that costs barely 5 euros.

## Key Features

* **Fluid Visualization:** A Python interface optimized to display thousands of data points per second without stuttering.
* **Uninterrupted Sampling:** Thanks to its intelligent design, the device never "blinks"; it captures the signal continuously and without gaps.
* **Robust Design:** Inspired by mission-critical systems, the software automatically detects data saturation or errors to alert you immediately.
* **Simulation Mode:** Don't have the board handy? It includes a virtual signal generator so you can test the interface and your analysis tools anywhere.

## How it works (At a glance)

1. **Capture:** The Raspberry Pi Pico collects the electrical signal at high speed.
2. **Transport:** The data travels via USB to your computer through an optimized "pipeline."
3. **Visualization:** The desktop application translates those numbers into a bright green graph, allowing you to analyze the signal comfortably.