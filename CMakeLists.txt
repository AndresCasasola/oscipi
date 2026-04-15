cmake_minimum_required(VERSION 3.13)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Initialise pico_sdk from installed location
# (note this can come from environment, CMake cache etc)

# == DO NOT EDIT THE FOLLOWING LINES for the Raspberry Pi Pico VS Code Extension to work ==
if(WIN32)
    set(USERHOME $ENV{USERPROFILE})
else()
    set(USERHOME $ENV{HOME})
endif()
set(sdkVersion 2.2.0)
set(toolchainVersion 14_2_Rel1)
set(picotoolVersion 2.2.0-a4)
set(picoVscode ${USERHOME}/.pico-sdk/cmake/pico-vscode.cmake)
if (EXISTS ${picoVscode})
    include(${picoVscode})
endif()
# ====================================================================================

set(PICO_BOARD pico CACHE STRING "Board type")

# Pull in Raspberry Pi Pico SDK (must be before project)
include(pico_sdk_import.cmake)

# Project name
project(oscipi C CXX ASM)

# Initialise the Raspberry Pi Pico SDK
pico_sdk_init()

# FreeRTOS Kernel Path
set(FREERTOS_KERNEL_PATH ${CMAKE_CURRENT_LIST_DIR}/FreeRTOS-Kernel)

# Add the RP2040 specific FreeRTOS port
add_subdirectory(FreeRTOS-Kernel/portable/ThirdParty/GCC/RP2040 FreeRTOS_Kernel)

# Add executable and main source file
add_executable(oscipi
    src/main.c
)

# Enable USB output for stdio (printf via USB)
pico_enable_stdio_usb(oscipi 1)

# Pull in common dependencies
target_link_libraries(oscipi 
    pico_stdlib
    FreeRTOS-Kernel-Heap4
)

# Tell FreeRTOS where the FreeRTOSConfig.h file is located
target_include_directories(oscipi PRIVATE ${CMAKE_CURRENT_LIST_DIR}/src)

# Create map/bin/hex/uf2 files
pico_add_extra_outputs(oscipi)