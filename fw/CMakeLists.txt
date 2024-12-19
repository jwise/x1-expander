cmake_minimum_required(VERSION 3.13...3.27)

# initialize pico-sdk from submodule
# note: this must happen before project()
include(pico-sdk/pico_sdk_init.cmake)

project(x1p_002_c_fw)

# initialize the Raspberry Pi Pico SDK
pico_sdk_init()

add_executable(x1p_002_c_fw main.c usb_descriptors.c)

pico_generate_pio_header(x1p_002_c_fw ${CMAKE_CURRENT_LIST_DIR}/ws2812.pio OUTPUT_DIR ${CMAKE_CURRENT_LIST_DIR}/generated)

# tusb_config.h
target_include_directories(x1p_002_c_fw PUBLIC ${CMAKE_CURRENT_LIST_DIR})

target_link_libraries(x1p_002_c_fw pico_stdlib pico_unique_id tinyusb_device tinyusb_board pico_usb_reset_interface_headers hardware_pio)

pico_enable_stdio_uart(x1p_002_c_fw 1)
add_definitions(-DPICO_DEFAULT_UART=1 -DPICO_DEFAULT_UART_TX_PIN=24 -DPICO_DEFAULT_UART_RX_PIN=25)

pico_set_binary_type(x1p_002_c_fw no_flash)

# create map/bin/hex/uf2 file etc.
pico_add_extra_outputs(x1p_002_c_fw)
