if (NOT PICO_SDK_PATH)
    if (DEFINED ENV{PICO_SDK_PATH})
        set(PICO_SDK_PATH $ENV{PICO_SDK_PATH})
    else()
        # Calculamos la ruta absoluta desde la raíz del proyecto
        get_filename_component(PICO_SDK_PATH "${CMAKE_CURRENT_SOURCE_DIR}/lib/pico-sdk" REALPATH)
    endif()
endif()

if (NOT EXISTS "${PICO_SDK_PATH}/pico_sdk_init.cmake")
    message(FATAL_ERROR "
      [BUNKER ERROR] Pico SDK not found at: ${PICO_SDK_PATH}
      Please check if 'lib/pico-sdk' contains the SDK files.")
endif()

set(PICO_SDK_PATH "${PICO_SDK_PATH}" CACHE PATH "Path to the Raspberry Pi Pico SDK" FORCE)
include(${PICO_SDK_PATH}/pico_sdk_init.cmake)