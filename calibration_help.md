[![Français](https://img.shields.io/badge/Langue-Fran%C3%A7ais-blue)](calibration_help.fr.md) [![English](https://img.shields.io/badge/Language-English-red)](#)
[← Back to README](README.md)

# 🎛️ Flipr Local - Calibration Guide

This document explains how to configure and fine-tune your Flipr probe calibration directly from the Home Assistant interface. 💡

---

## 1. ⚙️ Understanding calibration options

The **Flipr Local** integration is designed to be flexible and adapt to your technical comfort level. In the Configuration window (gear icon ⚙️), you can choose between two methods to fill in the **pH 7 Value** and **pH 4 Value** fields:

### 📱 Method A: Values from the official app
If you do not have your raw data, simply open the official Flipr app, navigate to **Menu > Expert Mode > Expert View** 🔍, and take note of the displayed pH values (e.g., `8.40` and `6.02`). Enter these values directly into Home Assistant.

<img src="docs/screenshots/flipr_calibration.png" width="400" alt="Flipr Calibration">

### ⚡ Method B: Raw millivolt values (Advanced)
The integration exposes a **Raw pH (mV)** entity that displays the raw voltage of your pH probe in mV 📉. Note the value once the Flipr is immersed and stabilized in the calibration solution (e.g., `1600` or `1900`), then enter these values directly in the configuration via the gear icon.

> 💡 **Note:** This diagnostic entity is **disabled by default**. To enable it during calibration, go to your Flipr device page (**Settings** > **Devices & services** > **Flipr**), click on the disabled entity, and toggle **Enable**.

![Raw pH (mV)](docs/screenshots/raw_ph_values_mv.png)

### 🔋 What about Redox (ORP)?
The principle is identical. The **Raw ORP (mV)** entity (also disabled by default) displays the **raw** value from the Redox probe, before any offset is applied. Immerse the Flipr into a Redox calibration solution (e.g., 650 mV), wait for the value to stabilize, then enter it into **ORP (Redox) Value**, and enter the reference value in **ORP (Redox) Solution Target**. The integration applies the difference to all readings.

> ⚠️ The two pH calibration points (pH 4 and pH 7) must be far enough apart. If they are too close, the calibration is degenerate: the integration ignores it and falls back to the factory calibration (and logs a warning) rather than displaying a distorted value.

---

## 2. 🌡️ Adjusting the solution "Target" (Temperature)

Water chemistry is highly sensitive to heat ☀️. In a pool protected by an enclosure, water warms up quickly, and this physical rule also applies to your calibration solutions!

The pH of a buffer solution varies slightly depending on its temperature when you immerse the probe 💧.
* 📦 Check the back of your calibration packet or bottle (for example, for pH 7.00).
* 📊 You will see a table indicating the exact value according to liquid temperature.
* 🎯 **Example:** At 20°C, a pH 7 solution is actually **7.02**.

<img src="docs/screenshots/ph_calibration_targets.png" width="500" alt="pH Solution Target">

This precise value is what you need to enter into the **Solution Target** fields. ✅

---

## 3. 🚨 Configuring alert thresholds

The integration automatically creates binary status sensors (pH Status, Redox Status, Temperature Status). You can define your own thresholds in the configuration:
* ⚖️ **pH Min / Max:** (Default: 6.90 - 7.50)
* 🛡️ **ORP Min / Max:** (Default: 650 - 800 mV)
* ❄️ **Min Temperature:** Useful to anticipate freezing risk during winter (Default: 6.0°C)
* 🥵 **Max Temperature:** Useful to prevent water from turning if it gets too hot (Default: 32.0°C)

If any reading exceeds these thresholds, the sensor switches to the "Problem" state ⚠️, making it easy to trigger your automations (notifications 📱, turning on filtration 🔄, etc.).

<img src="docs/screenshots/alert_thresholds.png" width="500" alt="Thresholds">