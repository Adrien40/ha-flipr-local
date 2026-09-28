[![Français](https://img.shields.io/badge/Langue-Fran%C3%A7ais-blue)](README.fr.md) [![English](https://img.shields.io/badge/Language-English-red)](#)

# Blue Connect Local for Home Assistant 🐬
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/Adrien40/ha-blue-connect-local)](https://github.com/Adrien40/ha-blue-connect-local/releases)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/github/actions/workflow/status/Adrien40/ha-blue-connect-local/tests.yaml?branch=main&label=tests)](https://github.com/Adrien40/ha-blue-connect-local/actions/workflows/tests.yaml)
[![HACS](https://img.shields.io/github/actions/workflow/status/Adrien40/ha-blue-connect-local/hacs.yaml?branch=main&label=hacs)](https://github.com/Adrien40/ha-blue-connect-local/actions/workflows/hacs.yaml)
[![Hassfest](https://img.shields.io/github/actions/workflow/status/Adrien40/ha-blue-connect-local/hassfest.yaml?branch=main&label=hassfest)](https://github.com/Adrien40/ha-blue-connect-local/actions/workflows/hassfest.yaml)
[![Linting](https://img.shields.io/github/actions/workflow/status/Adrien40/ha-blue-connect-local/ruff.yaml?branch=main&label=lint)](https://github.com/Adrien40/ha-blue-connect-local/actions/workflows/ruff.yaml)
[![Typing](https://img.shields.io/github/actions/workflow/status/Adrien40/ha-blue-connect-local/mypy.yaml?branch=main&label=mypy%20--strict)](https://github.com/Adrien40/ha-blue-connect-local/actions/workflows/mypy.yaml)
[![Quality Scale](https://img.shields.io/badge/HA%20Quality%20Scale-Platinum-e5e4e2)](custom_components/blue_connect_local/quality_scale.yaml)

If this project is useful to you, you can support its development 🙏

<a href="https://www.buymeacoffee.com/adrien40"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" width="160"></a>

---

## ⚡ At a Glance
- 🔌 100% local operation via Bluetooth (BLE)
- 🏠 Compatible with Home Assistant (no cloud)
- 🏷️ Automatic Model Detection (Gold / Silver)
- 🌡️ Measurements: Temperature, pH, ORP Redox, Salinity, Conductivity, Battery
- 🎯 Manual Analysis: Force a new water analysis on demand, remotely
- ⚖️ Floating Status
- 🔋 Optimized to preserve battery life
- ⚙️ Installation via HACS in 2 minutes

---

## 📸 Examples in Home Assistant

### 📊 Visualization

<p align="center">
  <img src="docs/screenshots/dashboard_overview.png" width="600">
</p>

<p align="center">
  <em>📊 Overview of pool data in Home Assistant</em>
</p>

---

### 🔍 Technical Details

<p align="center">
  <img src="docs/screenshots/entities_overview.png" width="600">
</p>

<p align="center">
  <em>🔍 Entities exposed by the integration & ⚙️ Advanced configuration options</em>
</p>

---

A **100% local integration for Home Assistant** that turns your Blue Connect analyzer into a Bluetooth Low Energy (BLE) sensor, letting you control and monitor your pool with zero dependency on the Cloud. 🛡️

> ⚠️ **Warning**: This integration queries the Blue Connect directly over Bluetooth.

### 💡 Why This Integration?
This integration frees your Blue Connect from the Cloud by directly leveraging its BLE protocol, for uncompromising home automation:

* **🔒 100% local:** Works without internet. Your data goes straight from the pool to Home Assistant.
* **⏱️ No API limits:** Passive listening to regular data frames, plus the ability to force a measurement on demand, with no restrictions.
* **🛡️ Longevity:** Total independence from official servers, so your hardware keeps working for the long haul.

**Blue Connect Local** is the result of in-depth **reverse engineering** work to turn your analyzer into a true local, industrial-grade sensor capable of communicating directly with your Home Assistant instance.
Blue Connect Local replaces the cloud with a **local control** solution, while offering a reliable **pool monitoring** system built on a **BLE sensor**.

---

### ✅ Compatibility / Requirements
* 🏷️ **Supported models**: ZODIAC Blue Connect (Gold / Silver) with **automatic detection and adaptation** of sensors (Conductivity and Salinity).
* 🏅 **Tested on**: Validated on the **ZODIAC Blue Connect Gold and Silver**.
* 🔑 **Access Code (Optional)**: Your device's 9-character access code. It isn't required for passive listening, but it is **essential** for on-demand analyses.
* 🛠️ **Required hardware**: Internal Bluetooth adapter, USB Bluetooth dongle, or an **ESPHome Bluetooth Proxy** (strongly recommended, [easy installation here](https://esphome.github.io/bluetooth-proxies/)).
* 📶 **Signal quality**: A stable RSSI signal (ideally **above -75 dBm**) is essential to guarantee a reliable connection to the Blue Connect. Testing shows that a signal below -90 dBm causes frequent read failures.
* ⏱️ **Real-time monitoring**: A `sensor.*_signal_bluetooth` entity uses Home Assistant's passive listening so you can watch signal strength live — all without draining the Blue Connect's battery!

> ❌ **Not compatible**: Blueriiot versions are not supported.

---

### ✨ Highlights
* 🏠 **100% Local (BLE)**: No Cloud dependency, no subscription, no latency.
* 🏷️ **Smart Model Detection**: Automatic identification of your device variant (Gold or Silver) in both active and passive modes. Conductivity and Salinity sensors are automatically enabled or disabled according to your hardware probe.
* 🌡️ **Raw sensor readings**: Temperature, pH, ORP (Redox), Salinity, Conductivity, Battery (%).
* 🚀 **Real-time analysis**: Trigger a manual measurement whenever you want.
* 🧪 **Advanced Chemical Intelligence**:
  * Calculates the **Langelier Saturation Index** (LSI) to tell you whether your water is balanced, scale-forming, or corrosive.
* 🟤 **Multi-treatment support**: Works with **Bromine** (automatically disables the CYA entity, which isn't relevant for that treatment) and with stabilizer-free pools (CYA = 0). The treatment type and the CYA level are kept for future use: **no calculated value depends on them at the moment**.
* ⚙️ **100% UI Configuration**: Automatic Bluetooth discovery, probe calibration, and alert threshold settings, all directly from the Home Assistant interface (no YAML required).
* 🔄 **Sync Modes**: Passive Mode (silent, battery-saving listening) and Active Mode (on-demand Bluetooth analyses via the access code).
* ⏱️ **Scheduled Analyses on Fixed Time Slots** (Active Mode): set an **Analysis Interval** and a **Reference Time**; analyses run at the same times every day instead of on a rolling interval (see *Scheduled Analyses* below).
* 🌍 **Multi-language**: Developed in French 🇫🇷 and available in EN, ES, DE, IT, NL, PL, PT, PT-BR, SV, RU, ZH-HANS, ZH-HANT, CS, HU, EL, HR, DA, NB (AI-translated).
* 📡 Turns your Blue Connect into a true **BLE sensor** for Home Assistant

---

### 🚀 Installation

#### Via HACS (Recommended)
This repository isn't (yet) in the official default list, so you'll need to add it as a custom repository.

1. Open **HACS** in your Home Assistant.
2. Click the 3 dots in the top-right corner and select **Custom repositories**.
3. Under **Repository**, paste the URL: `https://github.com/Adrien40/ha-blue-connect-local`
4. Under **Type**, choose **Integration**, then click **Add**.
5. Once added, a window will pop up: click **Download** (select the latest version).
6. **Fully restart Home Assistant**.
7. Go to **Settings** > **Devices & Services** > **Add Integration** and search for "Blue Connect Local".

### Manual
Copy the `custom_components/blue_connect_local` folder into the `custom_components` folder of your Home Assistant configuration, then restart.

### 🗑️ Removal
1. Go to **Settings** > **Devices & Services**, find your Blue Connect device, click the 3 dots and select **Delete**. This removes all entities and stops the Bluetooth polling/listening.
2. If installed via HACS: open **HACS**, find **Blue Connect Local**, click the 3 dots and select **Remove**.
3. If installed manually: delete the `custom_components/blue_connect_local` folder, then restart Home Assistant.

Removing the integration also deletes its locally stored history (last known values, calibration reference points, access code). If you only want to pause measurements without losing this data, use the **Automatic Analysis** switch instead of deleting the integration.

---

### 📊 Available Sensors and Controls
| Entity | Unit / Type | Description |
| :--- | :--- | :--- |
| 💧 **pH** | pH | Calculated pH (Nernst equation + thermal compensation). |
| ⚡ **Redox / ORP** | mV | Oxidation-reduction potential. |
| 🌡️ **Temperature** | °C | Precise water temperature. |
| 🧂 **Salinity** | g/L | Water salinity (automatically enabled on Blue Connect Gold). |
| 🧪 **Conductivity** | µS/cm | Electrical conductivity (automatically enabled on Blue Connect Gold). |
| ⚖️ **Langelier Saturation Index** | LSI | Water balance indicator (Corrosive, Balanced, or Scale-forming). |
| 🎯 **Equilibrium pH** | pH | Ideal pH target, calculated per the Taylor Balance. |
| 🔋 **Battery** | % and mV | Charge level (%) and raw battery voltage. |
| 📶 **RSSI Signal** | dBm | Real-time received Bluetooth signal strength. |
| 🔵 **Bluetooth Status** | Status | Detailed connection state (Connected, Standby, Error...). |
| ⏱️ **Next Analysis** | Timestamp | Estimated time of the next data reading. |
| 🚀 **New Analysis** | Button | **Trigger an instant analysis (~60s).** |
| ⏸️ **Automatic Analysis** | Switch | Turn automatic readings on/off (Pause Mode). |
| 🔄 **Analysis Interval** | Setting (min) | Time between two scheduled analyses (5 – 1440), Active Mode. |
| 🕒 **Reference Time** | Setting (time) | Time the analysis slots are anchored on (default 08:00). |
| 📡 **Blue Connect Internal Analysis (Passive)** | Switch | Use the readings the probe broadcasts on its own. |
| 💧 **TAC / TH / TDS / CyA** | Settings (mg/L, ppm) | Water parameters used for the Langelier index and the equilibrium pH (CyA is recorded for future use). |

> 🛠️ **Device Info & Diagnostics**: **Serial Number**, **Model Number (SKU)**, and **MAC Address** are natively integrated into the Home Assistant device header. The integration also exposes advanced diagnostic sensors (raw pH, raw ORP in mV, full raw hex frame, floating status, and binary alerts).

> ℹ️ **On Blue Connect Silver** (no conductivity probe): the Conductivity and Salinity entities are automatically disabled. If you updated an existing installation where Conductivity was already present, the integration now detects the Silver model and disables these entities on its own — no manual action needed.

---

### 🧪 Chemical Expertise: Professional-Grade Analysis

👉 No need to understand these calculations — Home Assistant automates everything.

<details>
<summary>🔬 See the scientific details</summary>

#### Water Balance: Langelier Saturation Index & Taylor Balance ⚖️
The Langelier Saturation Index (LSI) is the essential companion to the **Taylor Balance**. It tells you whether your water is:
* **Corrosive (LSI < -0.3)**: The water attacks your seals, liner, and metal parts.
* **Balanced (LSI between -0.3 and +0.3)**: Perfect water.
* **Scale-forming (LSI > +0.3)**: Risk of limescale buildup.

Enter your TAC (Total Alkalinity), TH (Total Hardness), and TDS in the options, and Home Assistant will calculate your balance live, based on the temperature read from the Blue Connect!

</details>

---

### 🎯 A Note on Measurement Accuracy
Values shown in Home Assistant may differ slightly from those in the official Blue Connect app.

Blue Connect Local supports "high-precision" calibration. Unlike the mobile app, which uses fixed values, our integration lets you enter the exact value of your buffer solution (pH 7.02, 4.01, etc.), adjusted for temperature during calibration. This scientific rigor is what can create a slight offset — a sign that the reading is actually closer to your pool's true conditions. 🔬

---

## 🚀 Configuration
> ⚠️ Requires **Home Assistant 2026.3.0 or newer** (the first release shipped with Python 3.14). Tested on 2026.3.0 and 2026.9.

1. Go to **Settings** > **Devices & Services**.
2. The integration should automatically detect your Blue Connect if your Bluetooth dongle/antenna is in range. Otherwise, click **Add Integration** and search for **Blue Connect Local**.
3. Follow the on-screen instructions to set your treatment type (Chlorine, Bromine) and your probe calibration/offset.

### ⚙️ Options, Calibration & Alerts
Once the device has been added, you can click **Configure** ⚙️ to:
* Adjust the values of your calibration solutions (pH 4, pH 7, Redox).
* Update your water parameters (TAC, TH, TDS, Stabilizer) directly via the exposed controls.
* Set the **Analysis Interval** and the **Reference Time** (⏱️ *Synchronization* section), see *Scheduled Analyses* below.
* Set your own **custom alert thresholds** (pH Min/Max, ORP Min/Max, etc.) to drive your own automations.

> Find the step-by-step procedure (raw pH / raw ORP, temperature compensation, and Alert Thresholds) in the **[Calibration Guide](calibration_help.md)**. Release notes are in the **[Changelog](CHANGELOG.md)**.

### ⏱️ Scheduled Analyses (Active Mode)
When an **Access Code** is set (Active Mode), automatic analyses are not run "every N minutes since the last one": they are aligned on **fixed time slots**, so you get readings at predictable times, whatever happened before (restart, manual analysis, error).

| Setting | Default | Range | Role |
| :--- | :--- | :--- | :--- |
| 🔄 **Analysis Interval** | 60 min | 5 – 1440 min | Time between two scheduled analyses. |
| 🕒 **Reference Time** | 08:00 | HH:MM | Time the slots are anchored on. |

* **Example**: with an interval of **120 min** and a reference time of **08:00**, analyses run at 08:00, 10:00, 12:00, 14:00… (and 06:00, 04:00… before it).
* **Where to change them**: **Configure** ⚙️ > **⏱️ Synchronization** section, or directly from the **Analysis Interval** and **Reference Time** entities of the device (configuration category), for instance on a dashboard.
* **Changes apply immediately**: the next analysis is re-planned as soon as you change either setting.
* **Tip**: pick an interval that divides 24 h evenly (5, 10, 15, 20, 30, 60, 120, 180, 240, 360, 480, 720 or 1440 min). Otherwise the slots shift from one day to the next, because they are re-anchored on the Reference Time every day.
* A slot less than 10 seconds away is skipped in favour of the following one.
* **New Analysis** (requires an access code) runs immediately and does not change the schedule.
* **Automatic Analysis** switched off: scheduled analyses are skipped. Switching it back on does **not** start an analysis by itself; the next one runs at the next slot (or press **New Analysis**).
* **Without an access code (Passive Mode)** there is no schedule: Home Assistant uses the readings the probe broadcasts on its own, about one per hour.

---

### 🐛 Troubleshooting

<details>
<summary>⚠️ See common issues</summary>
  
* **Frequent Bluetooth errors**: The integration automatically handles connection retries. If the sensor shows `Signal Lost`, the Blue Connect is out of range. Move your antenna closer, or [install an ESPHome Bluetooth Proxy](https://esphome.github.io/bluetooth-proxies/) as close to the pool as possible (all you need is an ESP32 (~€10) and a USB charger).
* **Invalid access code**: The integration checks your access code as soon as it connects, so if it's wrong you'll see `Invalid access code` on the Bluetooth Status sensor within seconds — no need to wait for the full analysis timeout. Home Assistant will also prompt you to re-enter it via a **Re-authenticate** notification; you can also fix it manually in **Configure ⚙️**, which triggers a new analysis automatically once you save.

</details>

### 🎯 Use Cases
* **Pool safety automation**: trigger a notification or turn off the filtration pump if pH or ORP drifts outside your safe range, using the `pH Status` / `ORP Redox Status` binary sensors.
* **Freeze protection**: combine the `Temperature Status` binary sensor with a heater or cover automation when winter temperatures approach freezing.
* **Chemical dosing reminders**: use the Langelier Index Status sensor to get notified when your water becomes corrosive or scale-forming, before it damages your equipment.
* **Passive-only monitoring**: without an access code, Blue Connect Local still gives you hourly readings from the probe's own broadcasts — useful if you don't want or need on-demand analyses.

### 🤖 Automation Examples

<details>
<summary>📋 Notify when pH goes out of range</summary>

```yaml
automation:
  - alias: "Pool pH out of range"
    trigger:
      - platform: state
        entity_id: binary_sensor.blue_connect_ph_status
        to: "on"
    action:
      - action: notify.mobile_app_your_phone
        data:
          title: "⚠️ Pool pH alert"
          message: "pH is currently {{ states('sensor.blue_connect_ph') }}, outside the configured range."
```
</details>

<details>
<summary>📋 Alert if the probe has not reported in a while</summary>

```yaml
automation:
  - alias: "Blue Connect unreachable too long"
    trigger:
      - platform: event
        event_type: repairs_issue_registry_updated
        event_data:
          action: create
          domain: blue_connect_local
    action:
      - action: notify.mobile_app_your_phone
        data:
          title: "🔌 Blue Connect unreachable"
          message: "The Blue Connect probe hasn't responded in a while. Check its battery and Bluetooth range."
```
</details>

### ⚠️ Known Limitations
* **Bluetooth range**: like any BLE device, Blue Connect needs to stay within range of a Bluetooth adapter or [ESPHome proxy](https://esphome.github.io/bluetooth-proxies/). Thick pool covers, distance, and metal structures can weaken the signal.
* **No push notifications from the probe**: on-demand analyses aside, data is refreshed on the scheduled time slots (Active Mode) or when the probe broadcasts its own reading, about once an hour (Passive Mode), not a live continuous stream.
* **ORP is not a chlorine measurement**: it reflects the oxidising strength of the water (pH, temperature, stabilizer, probe ageing), not a concentration. Use the raw ORP value with your own thresholds and a manual test kit for actual chlorine levels.
* **One probe per config entry**: if you own multiple Blue Connect units, add each one as a separate integration entry.
* **Blueriiot hardware is not supported**, only genuine ZODIAC Blue Connect Gold/Silver.

---

### 🤝 Contributing & Support
For any bugs or feature requests, please open an [Issue](https://github.com/Adrien40/ha-blue-connect-local/issues) on this repository.

### ⚠️ Disclaimer
This integration is an independent project. It has no affiliation whatsoever with the FLUIDRA/ZODIAC company. Use of this software is at your own risk.

### ⚖️ License
Project licensed under **GPLv3**. Independent of the FLUIDRA company. Use at your own risk.

---

**Built with ❤️ by @Adrien40**

<a href="https://www.buymeacoffee.com/adrien40"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" width="180"></a>

<!-- Keywords: Home Assistant custom integration, BLE sensor, pool monitoring, local control -->
