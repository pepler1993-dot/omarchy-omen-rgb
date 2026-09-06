// SPDX-License-Identifier: GPL-2.0
/**
 * @file omen_rgb.c
 * @brief Minimal kernel module to control the 4-zone keyboard RGB of HP Omen
 *        laptops via the HP WMI BIOS interface (command 0x20009).
 *
 * Exposes four sysfs files (zone0..zone3) under a platform device.
 * Reading a file returns the current "RRGGBB" hex color of that zone.
 * Writing "RRGGBB" sets that zone's color while preserving the rest of
 * the 128-byte firmware state buffer (only the 3 target bytes change).
 *
 * Target validated on: OMEN by HP Gaming Laptop 16-wd0xxx (board 8BA9).
 * GET confirmed working; current colors read back correctly at the
 * documented offsets (zone N at 25 + N*3, RGB order).
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/acpi.h>
#include <linux/wmi.h>
#include <linux/platform_device.h>
#include <linux/device.h>
#include <linux/mutex.h>
#include <linux/dmi.h>
#include <linux/hex.h>

/* HP WMI BIOS GUID (also claimed by hp-bioscfg; we only use 0x20009). */
#define HPWMI_BIOS_GUID "5FB7F034-2C63-45e9-BE91-3D44E2C707E4"

/* Magic signature expected by the HP BIOS WMI method ("SECU"). */
#define HPWMI_SIGNATURE 0x55434553

/* "command" field value (HP command id for 4-zone lighting). */
#define HPWMI_FOURZONE 0x20009 /* 131081 */

/* "commandtype" field values (sub-command). */
#define HPWMI_FOURZONE_COLOR_GET 2
#define HPWMI_FOURZONE_COLOR_SET 3
#define HPWMI_FOURZONE_BRIGHT_GET 4
#define HPWMI_FOURZONE_BRIGHT_SET 5

/* Zone color layout inside the 128-byte state buffer. */
#define FOURZONE_COUNT 4
#define ZONE_BASE_OFFSET 25 /* zone 0 red byte; each zone is 3 bytes (R,G,B) */
#define STATE_SIZE 128

/* Brightness lives in byte 0 of the BRIGHT_GET/SET buffer (range 0..255). */
#define BRIGHT_OFFSET 0
#define BRIGHT_MAX 255

/* Serialize read-modify-write of the firmware state across zones. */
static DEFINE_MUTEX(omen_rgb_lock);

static struct platform_device *omen_rgb_pdev;

/**
 * @brief Input/output argument block for the HP BIOS WMI method.
 */
struct bios_args {
	u32 signature;
	u32 command;
	u32 commandtype;
	u32 datasize;
	u8 data[STATE_SIZE];
};

/**
 * @brief Header prepended to the WMI method output buffer.
 */
struct bios_return {
	u32 sigpass;
	u32 return_code;
};

/**
 * @brief Map a desired output size to the HP WMI method id (pvsz).
 */
static inline int encode_outsize_for_pvsz(int outsize)
{
	if (outsize > 4096)
		return -EINVAL;
	if (outsize > 1024)
		return 5;
	if (outsize > 128)
		return 4;
	if (outsize > 4)
		return 3;
	if (outsize > 0)
		return 2;
	return 1;
}

/**
 * @brief Perform one HP BIOS WMI query (read or write).
 *
 * @param command     HP command id (e.g. HPWMI_FOURZONE).
 * @param commandtype Sub-command (GET or SET).
 * @param buffer      In/out data buffer (max STATE_SIZE bytes).
 * @param insize      Bytes of input to send from @p buffer.
 * @param outsize     Bytes of output to copy back into @p buffer.
 *
 * @return 0 on success, positive HP error code, or negative errno.
 */
static int omen_wmi_query(u32 command, u32 commandtype, void *buffer,
			  int insize, int outsize)
{
	int mid;
	int ret = 0;
	acpi_status status;
	union acpi_object *obj;
	struct bios_return *bios_return;
	struct bios_args args = {
		.signature = HPWMI_SIGNATURE,
		.command = command,
		.commandtype = commandtype,
		.datasize = insize,
		.data = { 0 },
	};
	struct acpi_buffer input = { sizeof(struct bios_args), &args };
	struct acpi_buffer output = { ACPI_ALLOCATE_BUFFER, NULL };

	mid = encode_outsize_for_pvsz(outsize);
	if (mid < 0)
		return mid;

	if (insize < 0 || insize > sizeof(args.data) || outsize < 0 || outsize > STATE_SIZE)
		return -EINVAL;
	memcpy(&args.data[0], buffer, insize);

	status = wmi_evaluate_method(HPWMI_BIOS_GUID, 0, mid, &input, &output);
	if (ACPI_FAILURE(status)) {
		kfree(output.pointer);
		return -EIO;
	}

	obj = output.pointer;
	if (!obj)
		return -EINVAL;

	if (obj->type != ACPI_TYPE_BUFFER || !obj->buffer.pointer ||
	    obj->buffer.length < sizeof(struct bios_return)) {
		ret = -EINVAL;
		goto out_free;
	}

	bios_return = (struct bios_return *)obj->buffer.pointer;
	ret = bios_return->return_code;
	if (ret)
		goto out_free;

	if (!outsize)
		goto out_free;

	if (obj->buffer.length < sizeof(*bios_return) + outsize) {
		ret = -EPROTO;
		goto out_free;
	}
	memcpy(buffer, obj->buffer.pointer + sizeof(*bios_return), outsize);

out_free:
	kfree(obj);
	return ret;
}

/**
 * @brief Read the full 128-byte zone state from firmware.
 */
static int fourzone_get_state(u8 *state)
{
	return omen_wmi_query(HPWMI_FOURZONE, HPWMI_FOURZONE_COLOR_GET, state,
			      STATE_SIZE, STATE_SIZE);
}

/**
 * @brief Write the full 128-byte zone state back to firmware.
 */
static int fourzone_set_state(u8 *state)
{
	return omen_wmi_query(HPWMI_FOURZONE, HPWMI_FOURZONE_COLOR_SET, state,
			      STATE_SIZE, STATE_SIZE);
}

/**
 * @brief Map a sysfs attribute name "zoneN" to its byte offset in the state.
 *
 * @return offset on success, -1 if the name is not a valid zone.
 */
static int zone_offset_from_name(const char *name)
{
	int idx;

	if (strncmp(name, "zone", 4) != 0)
		return -1;
	if (kstrtoint(name + 4, 10, &idx))
		return -1;
	if (idx < 0 || idx >= FOURZONE_COUNT)
		return -1;
	return ZONE_BASE_OFFSET + idx * 3;
}

/**
 * @brief sysfs read: return current "RRGGBB" color of the zone.
 */
static ssize_t zone_show(struct device *dev, struct device_attribute *attr,
			 char *buf)
{
	u8 state[STATE_SIZE] = { 0 };
	int off;
	int ret;

	off = zone_offset_from_name(attr->attr.name);
	if (off < 0)
		return -EINVAL;

	mutex_lock(&omen_rgb_lock);
	ret = fourzone_get_state(state);
	mutex_unlock(&omen_rgb_lock);
	if (ret)
		return ret < 0 ? ret : -EIO;

	return sysfs_emit(buf, "%02X%02X%02X\n", state[off + 0],
			  state[off + 1], state[off + 2]);
}

/**
 * @brief sysfs write: set zone color from "RRGGBB", preserving other bytes.
 *
 * Read-modify-write: fetch the whole state, change only this zone's 3
 * bytes, write it all back. This keeps the firmware's header/other zones
 * intact (byte 0 = 0x03 and other zone colors must be preserved).
 */
static ssize_t zone_store(struct device *dev, struct device_attribute *attr,
			  const char *buf, size_t count)
{
	u8 state[STATE_SIZE] = { 0 };
	u32 rgb;
	int off;
	int ret;

	off = zone_offset_from_name(attr->attr.name);
	if (off < 0)
		return -EINVAL;

	/* Accept exactly 6 hex digits (RRGGBB). */
	if (kstrtouint(buf, 16, &rgb))
		return -EINVAL;
	if (rgb > 0xFFFFFF)
		return -EINVAL;

	mutex_lock(&omen_rgb_lock);

	ret = fourzone_get_state(state);
	if (ret) {
		mutex_unlock(&omen_rgb_lock);
		return ret < 0 ? ret : -EIO;
	}

	state[off + 0] = (rgb >> 16) & 0xFF; /* red   */
	state[off + 1] = (rgb >> 8) & 0xFF;  /* green */
	state[off + 2] = rgb & 0xFF;         /* blue  */

	ret = fourzone_set_state(state);
	mutex_unlock(&omen_rgb_lock);
	if (ret)
		return ret < 0 ? ret : -EIO;

	return count;
}

/* One transaction for all four zones, preserving non-color firmware bytes. */
static ssize_t colors_show(struct device *dev, struct device_attribute *attr, char *buf)
{
	u8 state[STATE_SIZE] = { 0 };
	int ret;
	mutex_lock(&omen_rgb_lock);
	ret = fourzone_get_state(state);
	mutex_unlock(&omen_rgb_lock);
	if (ret)
		return ret < 0 ? ret : -EIO;
	return sysfs_emit(buf, "%02X%02X%02X %02X%02X%02X %02X%02X%02X %02X%02X%02X\n",
		state[25], state[26], state[27], state[28], state[29], state[30],
		state[31], state[32], state[33], state[34], state[35], state[36]);
}

static ssize_t colors_store(struct device *dev, struct device_attribute *attr,
			   const char *buf, size_t count)
{
	u8 state[STATE_SIZE] = { 0 };
	u8 colors[12];
	int i, ret;
	/* Exactly four six-digit colors, separated by spaces, optional newline. */
	if (count != 27 && !(count == 28 && buf[27] == '\n'))
		return -EINVAL;
	for (i = 0; i < 4; i++) {
		if (i < 3 && buf[i * 7 + 6] != ' ')
			return -EINVAL;
		if (hex2bin(colors + i * 3, buf + i * 7, 3))
			return -EINVAL;
	}
	mutex_lock(&omen_rgb_lock);
	ret = fourzone_get_state(state);
	if (!ret) {
		memcpy(state + ZONE_BASE_OFFSET, colors, sizeof(colors));
		ret = fourzone_set_state(state);
	}
	mutex_unlock(&omen_rgb_lock);
	return ret ? (ret < 0 ? ret : -EIO) : count;
}
static DEVICE_ATTR_RW(colors);

/* One device_attribute per zone: zone0..zone3, mode 0644. */
static DEVICE_ATTR(zone0, 0644, zone_show, zone_store);
static DEVICE_ATTR(zone1, 0644, zone_show, zone_store);
static DEVICE_ATTR(zone2, 0644, zone_show, zone_store);
static DEVICE_ATTR(zone3, 0644, zone_show, zone_store);

static struct attribute *omen_rgb_attrs[] = {
	&dev_attr_colors.attr,
	&dev_attr_zone0.attr,
	&dev_attr_zone1.attr,
	&dev_attr_zone2.attr,
	&dev_attr_zone3.attr,
	NULL,
};

static const struct attribute_group omen_rgb_group = {
	.name = "rgb_zones",
	.attrs = omen_rgb_attrs,
};

/**
 * @brief Module init: verify WMI presence, confirm GET works, create sysfs.
 */
static int __init omen_rgb_init(void)
{
	u8 state[STATE_SIZE] = { 0 };
	int ret;

	if (!dmi_match(DMI_SYS_VENDOR, "HP") || !dmi_match(DMI_BOARD_NAME, "8C77"))
		return -ENODEV;

	if (!wmi_has_guid(HPWMI_BIOS_GUID)) {
		pr_err("omen_rgb: HP BIOS WMI GUID not present\n");
		return -ENODEV;
	}

	/* Sanity check: make sure the firmware answers a GET before exposing. */
	ret = fourzone_get_state(state);
	if (ret) {
		pr_err("omen_rgb: initial COLOR_GET failed, error 0x%x\n", ret);
		return -EIO;
	}

	omen_rgb_pdev = platform_device_register_simple("omen_rgb", -1, NULL, 0);
	if (IS_ERR(omen_rgb_pdev))
		return PTR_ERR(omen_rgb_pdev);

	ret = sysfs_create_group(&omen_rgb_pdev->dev.kobj, &omen_rgb_group);
	if (ret) {
		platform_device_unregister(omen_rgb_pdev);
		return ret;
	}

	pr_info("omen_rgb: ready, zones at /sys/devices/platform/omen_rgb/rgb_zones/\n");
	return 0;
}

/**
 * @brief Module exit: remove sysfs group and unregister the device.
 */
static void __exit omen_rgb_exit(void)
{
	sysfs_remove_group(&omen_rgb_pdev->dev.kobj, &omen_rgb_group);
	platform_device_unregister(omen_rgb_pdev);
	pr_info("omen_rgb: unloaded\n");
}

module_init(omen_rgb_init);
module_exit(omen_rgb_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("omenkey");
MODULE_DESCRIPTION("HP Omen 4-zone keyboard RGB control via WMI");
MODULE_VERSION("0.4");
