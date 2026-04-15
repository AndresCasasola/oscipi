# 1. Check if Git is available
find_package(Git REQUIRED)

# Set the desired version
set(FREERTOS_TAG "V11.3.0")

# 2. Check if the FreeRTOS-Kernel folder is empty or missing
if(NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/lib/FreeRTOS-Kernel/include/FreeRTOS.h")
    message(STATUS "FreeRTOS-Kernel not found. Initializing...")
    execute_process(
        COMMAND ${GIT_EXECUTABLE} submodule update --init --recursive
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )
endif()

# 3. Force specific Tag/Version
# This ensures every developer (and the CI) uses the exact same version
message(STATUS "Checking out FreeRTOS version ${FREERTOS_TAG}...")
execute_process(
    COMMAND ${GIT_EXECUTABLE} checkout ${FREERTOS_TAG}
    WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/lib/FreeRTOS-Kernel"
    RESULT_VARIABLE GIT_CHECKOUT_RESULT
)

if(NOT GIT_CHECKOUT_RESULT EQUAL 0)
    message(FATAL_ERROR "Failed to checkout FreeRTOS ${FREERTOS_TAG}")
endif()

# 4. Set paths and add subdirectory
set(FREERTOS_KERNEL_PATH ${CMAKE_CURRENT_SOURCE_DIR}/lib/FreeRTOS-Kernel CACHE INTERNAL "")
add_subdirectory(${FREERTOS_KERNEL_PATH}/portable/ThirdParty/GCC/RP2040 FreeRTOS_Kernel_Build)