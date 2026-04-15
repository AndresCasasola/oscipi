get_filename_component(UNITY_PATH "${CMAKE_CURRENT_SOURCE_DIR}/lib/unity" REALPATH)

if (NOT EXISTS "${UNITY_PATH}/src/unity.h")
    message(FATAL_ERROR "[BUNKER ERROR] Unity not found at: ${UNITY_PATH}")
endif()

add_library(unity STATIC EXCLUDE_FROM_ALL ${UNITY_PATH}/src/unity.c)
target_include_directories(unity PUBLIC ${UNITY_PATH}/src)