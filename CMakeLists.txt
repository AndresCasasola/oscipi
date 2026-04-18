cmake_minimum_required(VERSION 3.13)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Set dependency paths
set(PICO_SDK_PATH "${CMAKE_CURRENT_SOURCE_DIR}/lib/pico-sdk")
set(FREERTOS_KERNEL_PATH "${CMAKE_CURRENT_SOURCE_DIR}/lib/FreeRTOS-Kernel")
set(UNITY_PATH "${CMAKE_CURRENT_SOURCE_DIR}/lib/unity")

set(PICO_BOARD pico CACHE STRING "Board type")

# --- Modular Imports ---
list(APPEND CMAKE_MODULE_PATH ${CMAKE_CURRENT_SOURCE_DIR}/cmake)
include(cmake/pico_sdk_import.cmake)
include(cmake/freertos_import.cmake)
include(cmake/unity_import.cmake)

# Project name
project(oscipi C CXX ASM)

# Initialise the Raspberry Pi Pico SDK
pico_sdk_init()

# Add executable and main source file
add_executable(oscipi
    src/main.c
    src/osc_dma.c
    src/osc_processing.c
    src/osc_comm.c
)

# Enable USB output for stdio (printf via USB)
pico_enable_stdio_usb(oscipi 1)

# Pull in common dependencies
target_link_libraries(oscipi 
    pico_stdlib
    FreeRTOS-Kernel-Heap4
    hardware_adc
    hardware_dma
)

# Tell FreeRTOS where the FreeRTOSConfig.h file is located
target_include_directories(oscipi PRIVATE ${CMAKE_CURRENT_LIST_DIR}/src)

# Create map/bin/hex/uf2 files
pico_add_extra_outputs(oscipi)