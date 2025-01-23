#include "pico/bootrom.h"
#include "pico/usb_reset_interface.h"

#include "tusb.h"
#include "device/usbd_pvt.h"

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
