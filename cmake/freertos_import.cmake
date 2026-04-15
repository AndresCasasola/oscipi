# cmake/freertos_import.cmake - Bunkerized Version

# 1. Define the local path within the bunker
set(FREERTOS_KERNEL_PATH "${CMAKE_CURRENT_SOURCE_DIR}/lib/FreeRTOS-Kernel")

# 2. Check if the library actually exists
if(NOT EXISTS "${FREERTOS_KERNEL_PATH}/include/FreeRTOS.h")
    message(FATAL_ERROR "
    [BUNKER ERROR] FreeRTOS-Kernel not found at: ${FREERTOS_KERNEL_PATH}
    Please run: git submodule update --init --recursive")
endif()

message(STATUS "Bunker: Found FreeRTOS-Kernel at ${FREERTOS_KERNEL_PATH}")

# 3. Add the RP2040 specific port
# This is what connects FreeRTOS with the Raspberry Pi Pico hardware
add_subdirectory(${FREERTOS_KERNEL_PATH}/portable/ThirdParty/GCC/RP2040 FreeRTOS_Kernel_Build)

# 4. Set path as internal cache for other parts of the project
set(FREERTOS_KERNEL_PATH ${FREERTOS_KERNEL_PATH} CACHE INTERNAL "")