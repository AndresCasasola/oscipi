# cmake/unity_import.cmake

if (NOT UNITY_PATH)
    set(UNITY_PATH "${CMAKE_CURRENT_SOURCE_DIR}/lib/unity")
endif()

# Definimos una librería de interfaz para Unity
# Así, en cualquier test solo tendrás que poner target_link_libraries(test_name unity)
add_library(unity STATIC 
    ${UNITY_PATH}/src/unity.c
)

target_include_directories(unity PUBLIC ${UNITY_PATH}/src)