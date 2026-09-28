[![Français](https://img.shields.io/badge/Langue-Fran%C3%A7ais-blue)](README.fr.md) [![English](https://img.shields.io/badge/Language-English-red)](#)

# Flipr Local for Home Assistant 🐬
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/Adrien40/ha-flipr-local)](https://github.com/Adrien40/ha-flipr-local/releases)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/github/actions/workflow/status/Adrien40/ha-flipr-local/tests.yaml?branch=main&label=tests)](https://github.com/Adrien40/ha-flipr-local/actions/workflows/tests.yaml)
[![Validate](https://img.shields.io/github/actions/workflow/status/Adrien40/ha-flipr-local/validate.yaml?branch=main&label=hassfest%2Fhacs)](https://github.com/Adrien40/ha-flipr-local/actions/workflows/validate.yaml)
[![Linting](https://img.shields.io/github/actions/workflow/status/Adrien40/ha-flipr-local/lint.yaml?branch=main&label=lint)](https://github.com/Adrien40/ha-flipr-local/actions/workflows/lint.yaml)
[![Typing](https://img.shields.io/github/actions/workflow/status/Adrien40/ha-flipr-local/mypy.yaml?branch=main&label=mypy%20--strict)](https://github.com/Adrien40/ha-flipr-local/actions/workflows/mypy.yaml)
[![CodeQL](https://img.shields.io/github/actions/workflow/status/Adrien40/ha-flipr-local/codeql.yaml?branch=main&label=codeql)](https://github.com/Adrien40/ha-flipr-local/actions/workflows/codeql.yaml)
[![Quality Scale](https://img.shields.io/badge/HA%20Quality%20Scale-Platinum-e5e4e2)](custom_components/flipr_local/quality_scale.yaml)

If you find this project useful, you can support its development 🙏

<a href="https://www.buymeacoffee.com/adrien40"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" width="160"></a>

---

## ⚡ Quick Summary
- 🔌 Works over Bluetooth (100% local)
- 🏠 Home Assistant compatible (cloud-free)
- 🌡️ Measurements: pH, ORP (Redox), Temperature
- 🔋 Optimized to preserve battery life
- ⚙️ Installed via HACS in 2 minutes

---

## 📸 Home Assistant Examples

### 📊 Overview

<p align="center">
  <img src="https://raw.githubusercontent.com/Adrien40/ha-flipr-local/main/docs/screenshots/dashboard_overview.png" width="500">
</p>

<p align="center">
  <em>📊 Dashboard overview of pool data in Home Assistant</em>
</p>

---

### 🔍 Technical Details

<p align="center">
  <img src="https://raw.githubusercontent.com/Adrien40/ha-flipr-local/main/docs/screenshots/entities_overview.png" width="248">
  <img src="https://raw.githubusercontent.com/Adrien40/ha-flipr-local/main/docs/screenshots/entities_configuration.png" width="248">
</p>

<p align="center">
  <em>🔍 Entities exposed by the integration & ⚙️ Advanced configuration options</em>
</p>

---

A **100% local integration for Home Assistant** that turns your Flipr analyzer into a Bluetooth Low Energy (BLE) sensor, allowing you to monitor and control your pool without any cloud dependency. 🛡️

> ⚠️ **Warning**: This integration directly polls the Flipr over Bluetooth. If you use the official Wi-Fi gateway alongside it, rigorous sync mode management is built-in to prevent battery drain.

### 💡 Why this integration?
As the company CTAC-TECH / Flipr is undergoing liquidation, access to their cloud servers has become uncertain. **Flipr Local** is the result of extensive **Reverse Engineering** to transform your analyzer into a reliable local industrial sensor, capable of communicating directly with your Home Assistant instance.
Flipr Local lets you replace the cloud with a **local control** solution, providing robust **pool monitoring** based on a **BLE sensor**.

---

### ✅ Compatibility
* 🏷️ **Supported Models**: Flipr AnalysR (All Bluetooth versions - with or without a subscription).
* 🌐 **Flexible Usage**: Works with or without the Flipr Connect Wi-Fi Gateway.
* 🏅 **Tested on**: Validated with **Flipr AnalysR 3** and **Flipr Start Max**.
* 🛠️ **Required Hardware**: Internal Bluetooth, USB Bluetooth dongle, or **ESPHome Bluetooth Proxy** (Highly recommended, [easy installation here](https://esphome.github.io/bluetooth-proxies/)).
* 📶 **Signal Quality**: A stable **RSSI signal (ideally above -75 dBm)** is critical to ensure connection to the Flipr. Testing shows that signals below **-80 dBm** can cause frequent failures.
* ⏱️ **Real-time Monitoring**: A `sensor.*_signal_bluetooth` entity, using passive listening in Home Assistant, lets you monitor the signal strength in real-time without draining the probe's battery!

> ❌ **Not Compatible**: Versions that operate exclusively via the Sigfox network are not supported.

---

### ✨ Key Features
* 🏠 **100% Local (BLE)**: No cloud dependency, no subscriptions, no latency.
* 🌡️ **Raw Sensor Data**: Temperature, pH, ORP (Redox), Battery (%).
* 🚀 **Real-time Analysis**: Trigger a manual measurement whenever you want.
* 🔬 **Scientific Accuracy**: pH calculation using the Nernst equation with temperature compensation.
* 🛜 **Gateway-Free**: The gateway is not required, but keeping it allows you to maintain cloud access on the official mobile app!
* 🧪 **Advanced Chemical Intelligence**:
  * **Langelier Saturation Index (LSI)** calculation to determine if the water is balanced, scaling, or corrosive.
  * **Equilibrium pH** (Taylor Balance) from Temperature, TAC, TH and TDS.
* 🟤 **Treatment Type & Stabilizer (CyA)**: you can record your treatment (Chlorine / Bromine) and your stabilizer level. These settings are kept for future use — **no calculated value depends on them at the moment**.
* ⚙️ **100% UI Configuration**: Automatic Bluetooth discovery, Probe Calibration, and Alert Thresholds setup directly from the Home Assistant interface (no YAML required).
* 🔄 **Sync Modes**: Control the sync mode (Sleep, Eco, Normal, Boost) for users with the Wi-Fi Gateway, preventing battery drain.
* ⏱️ **Scheduled Analyses on Fixed Time Slots**: set an **Analysis Interval** and a **Reference Time**; analyses run at the same times every day instead of on a rolling interval (see *Scheduled Analyses* below).
* 🌍 **Multi-language**: Developed in French 🇫🇷 and available in EN, ES, DE, IT, NL, PL, PT, PT-BR, SV, RU, ZH-HANS, ZH-HANT, CS, HU, EL, HR, DA, NB (AI translation).
* 📡 Transforms your Flipr into a true **BLE sensor** for Home Assistant.

---

### 🚀 Installation

#### Via HACS (Recommended)
As this repository is not (yet) in the official default list, you must add it as a custom repository.

1. Open **HACS** in Home Assistant.
2. Click the 3 dots in the top right corner and select **Custom repositories**.
3. In **Repository**, paste the URL: `https://github.com/Adrien40/ha-flipr-local`
4. In **Type**, choose **Integration**, then click **Add**.
5. Once added, a window appears: click **Download** (select the latest version).
6. **Completely restart Home Assistant**.
7. Go to **Settings** > **Devices & Services** > **Add Integration** and search for "Flipr Local".

### Manual
Copy the `custom_components/flipr_local` folder into the `custom_components` directory of your Home Assistant configuration, then restart.

### 🗑️ Removal
1. Go to **Settings** > **Devices & Services**, find your Flipr device, click the 3 dots and select **Delete**. This removes all entities and stops the Bluetooth polling.
2. If installed via HACS: open **HACS**, find **Flipr Local**, click the 3 dots and select **Remove**.
3. If installed manually: delete the `custom_components/flipr_local` folder, then restart Home Assistant.

Removing the integration also deletes its locally stored history (last known values, calibration reference points). If you only want to pause measurements without losing this data, use the **Automatic Analyses** switch instead of deleting the integration.

---

### 🌐 Managing the Wi-Fi Gateway (Flipr Connect)
The integration works perfectly alongside your official setup:

* **Without Gateway**: Home Assistant wakes the Flipr on the time slots defined by the **Analysis Interval** and the **Reference Time** (default: every 60 min, on the hour).
* **With Gateway**: Configure the Flipr to **Eco Mode** (2 measures/day) or **Sleep Mode** (0 measure/day) via the integration options. The official gateway handles the cloud sync, while Home Assistant reads the data locally without draining the battery.

---

### ⏱️ Scheduled Analyses (Analysis Interval & Reference Time)
Automatic analyses are not run "every N minutes since the last one": they are aligned on **fixed time slots**, so you get readings at predictable times, whatever happened before (restart, manual analysis, error).

| Setting | Default | Range | Role |
| :--- | :--- | :--- | :--- |
| 🔄 **Analysis Interval** | 60 min | 5 – 1440 min | Time between two scheduled analyses. |
| 🕒 **Reference Time** | 08:00 | HH:MM | Time the slots are anchored on. |

* **Example**: with an interval of **120 min** and a reference time of **08:00**, analyses run at 08:00, 10:00, 12:00, 14:00… (and 06:00, 04:00… before it).
* **Where to change them**: **Configure** ⚙️ > **⏱️ Synchronization** section, or directly from the **Analysis Interval** and **Reference Time** entities of the device (configuration category), for instance on a dashboard.
* **Changes apply immediately**: the next analysis is re-planned as soon as you change either setting.
* **Tip**: pick an interval that divides 24 h evenly (5, 10, 15, 20, 30, 60, 120, 180, 240, 360, 480, 720 or 1440 min). Otherwise the slots shift from one day to the next, because they are re-anchored on the Reference Time every day.
* A slot less than 10 seconds away is skipped in favour of the following one.
* **New Analysis** runs immediately and does not change the schedule.
* **Automatic Analyses** switched off: scheduled analyses are skipped. Switching it back on does **not** start an analysis by itself; the next one runs at the next slot (or press **New Analysis**).

---

### 📊 Available Sensors and Controls
| Entity | Unit / Type | Description |
| :--- | :--- | :--- |
| 💧 **pH** | pH | Calculated pH (Nernst + Temp Compensation). |
| ⚡ **ORP (Redox)** | mV | Oxidation-Reduction Potential. |
| 🌡️ **Temperature** | °C | Precise water temperature. |
| ⚖️ **Langelier Index** | LSI | Water balance indicator (Corrosive, Balanced, or Scaling). |
| 🎯 **Equilibrium pH** | pH | Target ideal pH calculated via the Taylor Balance. |
| 🔋 **Battery** | % and mV | Charge level (%) and raw battery voltage. |
| 📶 **Bluetooth Signal** | dBm | Real-time received Bluetooth signal strength (RSSI). |
| 🔵 **Bluetooth State** | Status | Detailed connection state (Connected, Sleeping, Error...). |
| 🔄 **Sync Mode** | Diagnostic | Current probe mode read from the BLE frame (Eco, Boost...). |
| ⏱️ **Next Analysis** | Timestamp | Estimated time of the next data poll. |
| 🚀 **New Analysis** | Button | **Trigger an instant analysis (~60s).** |
| ⏸️ **Automatic Analyses** | Switch | Enable/Disable automatic polling (Pause Mode). |
| 🔄 **Analysis Interval** | Setting (min) | Time between two scheduled analyses (5 – 1440). |
| 🕒 **Reference Time** | Setting (time) | Time the analysis slots are anchored on (default 08:00). |
| 🧪 **Water Treatment** | Setting | Chlorine or Bromine (recorded, no calculated value depends on it yet). |
| 💧 **TAC / TH / TDS / CyA** | Settings (mg/L, ppm) | Water parameters used for the Langelier index and the equilibrium pH (CyA is recorded for future use). |

> 🛠️ **Diagnostic**: The integration also exposes advanced sensors (Raw pH in mV, Raw ORP in mV, Factory pH, Raw Hex Frame, and binary alert statuses). Most of these are **disabled by default** (they duplicate a calibrated value) — enable them from the entity settings if needed.

---

### 🧪 Chemical Expertise: Professional-Grade Analysis

👉 No need to understand these calculations: everything is automated in Home Assistant.

<details>
<summary>🔬 View scientific details</summary>

#### 1. Why there is no chlorine sensor 🧂
Versions before 1.2.0 displayed an *Estimated Free Chlorine* (ppm) and an *Active Chlorine – HOCl* (mg/L). They were **removed on purpose**, for these reasons:

* **ORP is not a concentration.** The Redox probe measures the oxidising strength of the water. For the same amount of chlorine, the reading changes with pH, temperature, stabilizer (CyA), other oxidisers, and with the ageing or fouling of the probe. Turning one mV value into "x ppm" hides all of these unknowns.
* **The conversion could show chlorine where there is none.** The formula was floored at 415 mV: every ORP below that gave the same result. At pH 7.2 without stabilizer, an ORP of **100 mV** (no oxidiser at all) still displayed **0.1 ppm** of free chlorine and **0.07 mg/L** of HOCl.
* **The stabilizer corrections were stacked and never validated.** Free chlorine was multiplied by CyA/40, then HOCl divided again by a CyA factor. With the same ORP (700 mV), pH (7.2) and temperature (25 °C), HOCl went from **0.66 mg/L** with no stabilizer to **0.02 mg/L** with 40 mg/L: a ×33 swing driven by a number typed by hand that changes during the season. No measurement data in this repository backs these factors.
* **The documentation promised more than the code did** (a "Machine Learning" model, a "thermodynamic model"), which gave a false sense of accuracy.
* **Chlorine is a safety measure.** A wrong value that looks precise is worse than no value.

**What to use instead:** the **ORP (Redox)** value with your own Alert Thresholds, the new **Raw ORP (mV)** diagnostic sensor to calibrate the probe on a reference solution, and a test kit or strips for the actual chlorine level.

#### 2. Water Balance: Langelier Saturation Index & Taylor Balance ⚖️
The Langelier Saturation Index (LSI) is the essential companion to the **Taylor Balance**. It determines if your water is:
* **Corrosive (LSI < -0.3)**: The water is eating away at your seals, liner, and metals.
* **Balanced (LSI between -0.3 and +0.3)**: Perfect water.
* **Scaling (LSI > +0.3)**: Risk of calcium deposits.

Enter your Alkalinity (TAC), Hardness (TH), and TDS in the options, and Home Assistant will calculate your balance live based on the temperature read by the Flipr!

> **Diagnostic**: The integration also exposes the Raw pH (mV), the Raw ORP (mV), the Factory-calculated pH, the full hex frame, and the timestamp of the Last Analysis. The raw and factory values are **disabled by default** — enable them from the entity settings if needed.

</details>

### 🎯 A Note on Measurement Accuracy
The values displayed in Home Assistant may differ slightly from the official Flipr app.

Flipr Local enables "High-Precision" calibration. Unlike the mobile app, which uses fixed values, our integration allows you to enter the exact value of your buffer solution (pH 7.02, 4.01, etc.) adjusted for temperature during calibration. This scientific rigor may create a slight discrepancy, indicating a measurement that is closer to the reality of your pool. 🔬

---

## 🚀 Configuration
> ⚠️ Requires **Home Assistant 2026.3.0 or newer** (the first release shipped with Python 3.14). Tested on 2026.3.0 and 2026.9.3.

1. Go to **Settings** > **Devices & Services**.
2. The integration should automatically discover your Flipr if your Bluetooth adapter/antenna is in range.
3. Click **Add Integration** and search for **Flipr Local**.
4. Follow the on-screen instructions to define the Treatment Type (Chlorine, Bromine), the Stabilizer level and the calibration of your probes.

### ⚙️ Options, Calibrations, and Alerts
Once the device is added, you can click on **Configure** ⚙️ to:
* Adjust your calibration solution values (pH 4, pH 7, ORP).
* Modify your water parameters (TAC, TH, TDS, Stabilizer) via the dashboard.
* Set the **Analysis Interval** and the **Reference Time** (⏱️ *Synchronization* section), see *Scheduled Analyses* above.
* Define your **custom Alert Thresholds** (Min/Max pH, Min/Max ORP, etc.) to trigger your own automations.

> 📖 **Need help calibrating your probes?**  
> Find the step-by-step procedure (official app method vs. raw mV values, temperature compensation, and Alert Thresholds) in the **[Calibration Guide](calibration_help.md)**. Release notes are in the **[Changelog](CHANGELOG.md)**.

---

### 🐛 Troubleshooting

<details>
<summary>⚠️ View common issues</summary>
  
* **Frequent Bluetooth errors**: The integration automatically handles connection retries. If the sensor shows `Signal Lost`, the Flipr is out of range. Move your antenna closer or [install an ESPHome Bluetooth Proxy](https://esphome.github.io/bluetooth-proxies/) as close to the pool as possible (only requires an ESP32 (~10€) and a USB charger).
* **The Free/Active Chlorine sensors disappeared after updating to 1.2.0**: this is intended (see *Why there is no chlorine sensor*). The orphan entities are removed automatically; delete them from your dashboards if needed.
* **I don't use stabilizer**: Simply set the `CyA (Stabilizer)` entity to `0`. It currently has no effect on any calculated value.

</details>

---

### 🎯 Use Cases
* **Pool safety automation**: trigger a notification or turn off the filtration pump if pH or ORP drifts outside your safe range, using the `pH Status` / `ORP Status` binary sensors.
* **Freeze protection**: combine the `Temperature Status` binary sensor with a heater or cover automation when winter temperatures approach freezing.
* **Chemical dosing reminders**: use the Langelier Index Status sensor to get notified when your water becomes corrosive or scale-forming, before it damages your equipment.
* **Battery-aware maintenance**: get a low-battery notification well before the probe stops responding, instead of discovering it during your next pool check.

### 🤖 Automation Examples

<details>
<summary>📋 Notify when pH goes out of range</summary>

```yaml
automation:
  - alias: "Pool pH out of range"
    trigger:
      - platform: state
        entity_id: binary_sensor.flipr_ph_status
        to: "on"
    action:
      - action: notify.mobile_app_your_phone
        data:
          title: "⚠️ Pool pH alert"
          message: "pH is currently {{ states('sensor.flipr_ph') }}, outside the configured range."
```
</details>

<details>
<summary>📋 Alert if the probe has not reported in a while</summary>

```yaml
automation:
  - alias: "Flipr unreachable too long"
    trigger:
      - platform: event
        event_type: repairs_issue_registry_updated
        event_data:
          action: create
          domain: flipr_local
    action:
      - action: notify.mobile_app_your_phone
        data:
          title: "🔌 Flipr unreachable"
          message: "The Flipr probe hasn't responded in a while. Check its battery and Bluetooth range."
```
</details>

### ⚠️ Known Limitations
* **Bluetooth range**: like any BLE device, the Flipr needs to stay within range of a Bluetooth adapter or [ESPHome proxy](https://esphome.github.io/bluetooth-proxies/). Thick pool covers, distance, and metal structures can weaken the signal.
* **No push notifications from the probe**: data is only refreshed on the scheduled time slots (or on-demand via the button) — this is not a live, continuous stream.
* **ORP is not a chlorine measurement**: see *Why there is no chlorine sensor* above. Use the raw ORP value with your own thresholds and a manual test kit for actual chlorine levels.
* **One probe per config entry**: if you own multiple Flipr units, add each one as a separate integration entry.

---

### 🛠️ Hardware Rescue

<details>
<summary>🔧 View the complete procedure</summary>

If your Flipr probes are dead, you can replace them yourself!

**Hardware required:**
1. Replacement probes (pH and ORP) with a BNC connector (Recommended dimensions: **12 mm diameter, 15-16 cm long**).
2. Two adapter cables (**Pigtails**): `Right-angle MMCX Male (90°) to BNC Female`. *The right-angle connector is essential to be able to close the Flipr cover.*

**Quick Procedure:**
Remove the old probes, clean the white base. Plug the MMCX adapters into the motherboard (`PH` and `ORP` ports). Pass the new probes through the original holes (12 mm), connect them to the BNC cables. Calibrate via Home Assistant, and you're good to go!

</details>

---

### 🤝 Contributions & Support
If you own an older version of the Flipr (1 or 2) and the integration works for you, please let us know!
For any bugs or feature requests, please open an [Issue](https://github.com/Adrien40/ha-flipr-local/issues) on this repository.

### ⚠️ Disclaimer
This integration is an independent project. It has no affiliation, directly or indirectly, with the company CTAC-TECH / Flipr. Use this software at your own risk.

### ⚖️ License
Project licensed under **GPLv3**. Independent from the Flipr company. Use entirely at your own risk.

---

**Developed with ❤️ by @Adrien40**

<a href="https://www.buymeacoffee.com/adrien40"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" width="180"></a>
