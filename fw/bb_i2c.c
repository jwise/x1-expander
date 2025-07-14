#include "hardware/pio.h"
#include "hardware/structs/pads_bank0.h"
#include "hardware/structs/pads_qspi.h"
#include "hardware/structs/io_qspi.h"

/* the PIO I2C implementation is trash garbage; we do it in a blocking
 * fashion anyway so may as well just bitbang it */

static void setup_pin(int pin) {
	sio_hw->gpio_oe_clr = 1 << pin;
	sio_hw->gpio_clr = 1 << pin;
	pads_bank0_hw->io[pin] = PADS_BANK0_GPIO0_IE_BITS | PADS_BANK0_GPIO0_PUE_BITS | PADS_BANK0_GPIO0_DRIVE_BITS;
	io_bank0_hw->io[pin].ctrl = GPIO_FUNC_SIO;
}

#define ZERO(pin) (sio_hw->gpio_oe_set = 1 << (pin))
#define ONE(pin)  (sio_hw->gpio_oe_clr = 1 << (pin))
#define READ(pin) ((sio_hw->gpio_in & (1 << (pin))) != 0)
static void wait() {
	for (int i = 0; i < 100; i++)
		asm volatile("nop");
}

static void start(int scl, int sda) {
	ONE(sda);
	ONE(scl);
	wait();
	ZERO(sda);
	wait();
	ZERO(scl);
	wait();
}

static void restart(int scl, int sda) {
	ONE(sda);
	wait();
	ONE(scl);
	wait();
	ZERO(sda);
	wait();
	ZERO(scl);
	wait();
}

static void stop(int scl, int sda) {
	ZERO(sda);
	wait();
	ONE(scl);
	wait();
	ONE(sda);
	wait();
}

static int wr(int scl, int sda, uint8_t byte) {
	for (int i = 0; i < 8; i++) {
		ZERO(scl);
		if (byte & 0x80)
			ONE(sda);
		else
			ZERO(sda);
		wait();
		asm volatile("nop\nnop\nnop\nnop\n");
		byte <<= 1;
		ONE(scl);
		wait();
		ZERO(scl);
	}
	wait();
	ONE(sda);
	ONE(scl);
	wait();
	int ack = !READ(sda);
	ZERO(scl);
	wait();
	return ack;
}

static uint8_t rd(int scl, int sda, int ack) {
	uint8_t d = 0;
	ONE(sda); /* should already be this way */
	for (int i = 0; i < 8; i++) {
		d <<= 1;
		ONE(scl);
		while (!READ(scl) /* ... timeout ... */)
			;
		wait();
		if (READ(sda))
			d |= 1;
		ZERO(scl);
		wait();
	}
	if (ack)
		ZERO(sda);
	else
		ONE(sda);
	wait();
	ONE(scl);
	wait();
	ZERO(scl);
	wait();
	ONE(sda);
	
	return d;
}

int bb_i2c_read(int scl, int sda, uint8_t addr, uint8_t *buf, size_t len) {
	setup_pin(scl);
	setup_pin(sda);
	
	int ack = 0;
	
	start(scl, sda);
	ack = wr(scl, sda, (addr << 1) | 1);
	if (!ack)
		goto fail;
	
	while (len--) {
		*(buf++) = rd(scl, sda, len != 0);
	}

fail:
	stop(scl, sda);
	return ack ? 0 : -1;
}


int bb_i2c_write(int scl, int sda, uint8_t addr, uint8_t *buf, size_t len) {
	setup_pin(scl);
	setup_pin(sda);
	
	int ack = 0;
	
	start(scl, sda);
	ack = wr(scl, sda, addr << 1);
	if (!ack)
		goto fail;
	
	while (len--) {
		ack = wr(scl, sda, *(buf++));
		if (!ack)
			goto fail;
	}

fail:
	stop(scl, sda);
	return ack ? 0 : -1;
}

int bb_i2c_write_read(int scl, int sda, uint8_t addr, uint8_t *buf, size_t wrlen, size_t rdlen) {
	setup_pin(scl);
	setup_pin(sda);
	
	int ack = 0;
	
	start(scl, sda);
	ack = wr(scl, sda, addr << 1);
	if (!ack)
		goto fail;
	
	uint8_t *wrbuf = buf;
	while (wrlen--) {
		ack = wr(scl, sda, *(wrbuf++));
		if (!ack)
			goto fail;
	}
	
	restart(scl, sda);
	ack = wr(scl, sda, (addr << 1) | 1);
	if (!ack)
		goto fail;
	while (rdlen--) {
		*(buf++) = rd(scl, sda, rdlen != 0);
	}

fail:
	stop(scl, sda);
	return ack ? 0 : -1;
}

