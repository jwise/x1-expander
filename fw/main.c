#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#include "pico/bootrom.h"

#include "pico/usb_reset_interface.h"
#include "bsp/board_api.h"
#include "tusb.h"

#include "usb_descriptors.h"

#include "device/usbd_pvt.h"

#include "hardware/pio.h"
#include "hardware/structs/pads_bank0.h"
#include "hardware/structs/pads_qspi.h"
#include "hardware/structs/io_qspi.h"
#include "ws2812.pio.h"
#include "pio_i2c.h"

void put_ws2812(int pin, uint8_t *buf, int pixels) {
	PIO pio = pio0;
	int sm = 0;
	pio_clear_instruction_memory(pio);
	uint offset = pio_add_program(pio, &ws2812_program);

	ws2812_program_init(pio, sm, offset, pin, 800000 /* freq */, 0 /* is_rgbw */);

	for (int i = 0; i < pixels; i++) {
		uint32_t pxl = 0;
		pxl = (pxl | *(buf++)) << 8;
		pxl = (pxl | *(buf++)) << 8;
		pxl = (pxl | *(buf++)) << 8;
		pio_sm_put_blocking(pio, sm, pxl);
	}
	uint32_t stall_mask = 1 << (PIO_FDEBUG_TXSTALL_LSB + sm);
	pio->fdebug = stall_mask;
	while ((pio->fdebug & stall_mask) == 0)
		;
	pio_sm_set_enabled(pio, sm, false);
}


uint8_t xbuf[512];

void do_read(void *buf, int len) {
	while (len) {
		while (tud_vendor_available() == 0) {
			/* timeout ... */
			/* check for disconnect ... */
			tud_task();
		}
		int n = tud_vendor_read(buf, len);
		buf += n;
		len -= n;
	}	
}

void do_i2c() {
	uint8_t sda, scl;
	do_read(&scl, 1);
	do_read(&sda, 1);
	
	PIO pio = pio0;
	int sm = 0;
	pio_clear_instruction_memory(pio);
	uint offset = pio_add_program(pio, &i2c_program);
	i2c_program_init(pio, sm, offset, sda, scl);

	printf("enter i2c subcmd, sda %d, scl %d\n", sda, scl);
	while (1) {
		uint8_t cmd;
		do_read(&cmd, 1);
		
		switch (cmd) {
		case 0x00:
			printf("done\n");
			goto alldone;
		case 0x01: /* read */ {
			uint8_t addr;
			uint8_t bytes;
			
			do_read(&addr, 1);
			do_read(&bytes, 1);
			
			printf("read %d bytes from adr %02x\n", bytes, addr);
			
			int result = pio_i2c_read_blocking(pio, sm, addr, xbuf, bytes);
			printf("  -> %d\n", result);
			tud_vendor_write(&result, 1);
			if (bytes)
				tud_vendor_write(xbuf, bytes);
			break;
		}
		case 0x02: /* write */ {
			uint8_t addr;
			uint8_t bytes;
			
			do_read(&addr, 1);
			do_read(&bytes, 1);
			do_read(xbuf, bytes);
			
			printf("write %d bytes to adr %02x\n", bytes, addr);
			
			int result = pio_i2c_write_blocking(pio, sm, addr, xbuf, bytes);
			printf("  -> %d\n", result);
			tud_vendor_write(&result, 1);
			break;
		}
		}
	}
alldone:
	tud_vendor_write_flush();
}

int main(void)
{
	board_init();
	tud_init(BOARD_TUD_RHPORT);

	if (board_init_after_tusb) {
		board_init_after_tusb();
	}

	while (1) {
		tud_task(); // tinyusb device task
		if (tud_mounted()) {
			/* kick watchdog */
		}
		
		/* handle the vendor RX FIFO */
		if (tud_vendor_available() >= 1) {
			uint8_t cmd;
			do_read(&cmd, 1);
			
			switch (cmd) {
			case 0x01: { /* ws2812 */
				uint16_t len;
				uint8_t pin;
				do_read(&len, 2);
				do_read(&pin, 1);
				printf("vendor: got ws2812 command for %d bytes on pin %d\n", len, pin);
				do_read(xbuf, len);
				printf("vendor: got data\n");
				put_ws2812(pin, xbuf, len / 3);
				break;
			}
			case 0x02: { /* configure gpio */
				uint8_t pin;
				uint8_t cfg;
				do_read(&pin, 1);
				do_read(&cfg, 1);
				uint8_t padcfg = PADS_BANK0_GPIO0_IE_BITS | PADS_BANK0_GPIO0_DRIVE_BITS | ((cfg & 1) ? PADS_BANK0_GPIO0_PUE_BITS : 0) | ((cfg & 2) ? PADS_BANK0_GPIO0_PDE_BITS : 0);
				if (pin < 32) {
					pads_bank0_hw->io[pin] = padcfg;
					io_bank0_hw->io[pin].ctrl = GPIO_FUNC_SIO;
					if (cfg & 4) {
						sio_hw->gpio_oe_set = 1 << pin;
					} else {
						sio_hw->gpio_oe_clr = 1 << pin;
					}
					if (cfg & 8) {
						sio_hw->gpio_set = 1 << pin;
					} else {
						sio_hw->gpio_clr = 1 << pin;
					}
				} else {
					pads_qspi_hw->io[pin - 32] = padcfg;
					io_qspi_hw->io[pin - 32].ctrl = GPIO_FUNC1_SIO;
					if (cfg & 4) {
						sio_hw->gpio_hi_oe_set = 1 << (pin - 32);
					} else {
						sio_hw->gpio_hi_oe_clr = 1 << (pin - 32);
					}
					if (cfg & 8) {
						sio_hw->gpio_hi_set = 1 << (pin - 32);
					} else {
						sio_hw->gpio_hi_clr = 1 << (pin - 32);
					}
				}
				gpio_put(pin, (cfg & 8) == 8);
				gpio_set_dir(pin, (cfg & 4) == 4);
				printf("vendor: set pin %d gpio %02x\n", pin, cfg);
				break;
			}
			case 0x03: { /* read GPIO */
				uint8_t pin;
				do_read(&pin, 1);
				uint8_t data;
				if (pin < 32) {
					data = (sio_hw->gpio_in & (1 << pin)) != 0;
				} else {
					data = (sio_hw->gpio_hi_in & (1 << (pin - 32))) != 0;
				}
				printf("vendor: pin %d is value %d\n", pin, data);
				tud_vendor_write(&data, 1);
				tud_vendor_write_flush();
				break;
			}
			case 0x04: { /* do I2C subcommand */
				do_i2c();
				break;
			}
			default:
				printf("vendor: unknown command %02x\n", cmd);
			}
		}
	}
}

void tud_mount_cb(void) {
	printf("USB connected\n");
}

void tud_umount_cb(void) {
	printf("USB disconnected\n");
}

void tud_suspend_cb(bool remote_wakeup_en) {
}

void tud_resume_cb(void) {
}

/* we do not use vendor_rx_cb / vendor_tx_cb since we handle these synchronously in the main processing loop */
#if 0
void tud_vendor_rx_cb(uint8_t itf, uint8_t const* buf, uint16_t bufsz) {
	printf("vendor: got %d bytes on itf %d\n", bufsz, itf);
}

void tud_vendor_tx_cb(uint8_t itf, uint32_t sent_bytes) {
	printf("vendor: did tx %ld bytes on itf %d\n", sent_bytes, itf);
}
#endif

/* RP2040 reset interface code */
int reset_itf_num = -1;

static void resetd_init(void) {
}

static void resetd_reset(uint8_t __unused rhport) {
	reset_itf_num = 0;
}

static uint16_t resetd_open(uint8_t __unused rhport, tusb_desc_interface_t const *itf_desc, uint16_t max_len) {
	TU_VERIFY(TUSB_CLASS_VENDOR_SPECIFIC == itf_desc->bInterfaceClass &&
	          RESET_INTERFACE_SUBCLASS == itf_desc->bInterfaceSubClass &&
	          RESET_INTERFACE_PROTOCOL == itf_desc->bInterfaceProtocol, 0);

	uint16_t const drv_len = sizeof(tusb_desc_interface_t);
	TU_VERIFY(max_len >= drv_len, 0);

	reset_itf_num = itf_desc->bInterfaceNumber;
	return drv_len;
}

// Support for parameterized reset via vendor interface control request
static bool resetd_control_xfer_cb(uint8_t __unused rhport, uint8_t stage, tusb_control_request_t const * request) {
	// nothing to do with DATA & ACK stage
	if (stage != CONTROL_STAGE_SETUP) return true;

	if (request->wIndex == reset_itf_num) {

		if (request->bRequest == RESET_REQUEST_BOOTSEL) {
			reset_usb_boot(0 /* gpio_mask */, (request->wValue & 0x7f));
			// does not return, otherwise we'd return true
		}

	}
	return false;
}

static bool resetd_xfer_cb(uint8_t __unused rhport, uint8_t __unused ep_addr, xfer_result_t __unused result, uint32_t __unused xferred_bytes) {
	return true;
}

static usbd_class_driver_t const _resetd_driver =
{
#if CFG_TUSB_DEBUG >= 2
	.name = "RESET",
#endif
	.init             = resetd_init,
	.reset            = resetd_reset,
	.open             = resetd_open,
	.control_xfer_cb  = resetd_control_xfer_cb,
	.xfer_cb          = resetd_xfer_cb,
	.sof              = NULL
};

// Implement callback to add our custom driver
usbd_class_driver_t const *usbd_app_driver_get_cb(uint8_t *driver_count) {
	*driver_count = 1;
	return &_resetd_driver;
}
