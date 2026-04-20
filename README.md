[![Français](https://img.shields.io/badge/Langue-Fran%C3%A7ais-blue)](README.fr.md) [![English](https://img.shields.io/badge/Language-English-red)](#)

# Flipr Local for Home Assistant 🐬
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/Adrien40/ha-flipr-local)](https://github.com/Adrien40/ha-flipr-local/releases)

If you find this project useful, you can support its development 🙏

<a href="https://www.buymeacoffee.com/adrien40"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" width="160"></a>

---

## ⚡ Quick Summary
- 🔌 Works over Bluetooth (100% local)
- 🏠 Home Assistant compatible (cloud-free)
- 🌡️ Measurements: pH, ORP (Redox), Active Chlorine, Temperature
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
* 🌐 **Flexible Usage**: Works with or without the Flipr Connect Wi-Fi gateway.
* 🏅 **Tested on**: Validated with **Flipr AnalysR 3**.
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
  * **Estimated Free Chlorine (FC)** calculated via the Nernst model (ORP + pH).
  * **Active Chlorine (HOCl)** calculated via the thermodynamic model (O'Brien / USEPA), accounting for temperature and stabilizer (CYA).
* 🟤 **Multi-Treatment Support**: Supports **Bromine** (intelligently disables chlorine-specific sensors) and pools without stabilizer (CYA = 0).
* ⚙️ **100% UI Configuration**: Automatic Bluetooth discovery, probe calibration, and alert threshold setup directly from the Home Assistant interface (no YAML required).
* 🔄 **Sync Modes**: Control the sync mode (Sleep, Eco, Normal, Boost) for users with the Wi-Fi gateway, preventing battery drain.
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

---

### 🌐 Managing the Wi-Fi Gateway (Flipr Connect)
The integration works perfectly alongside your official setup:

* **WITHOUT Gateway**: Home Assistant wakes the Flipr according to the polling interval you selected (default: every 60 min).
* **WITH Gateway**: Configure the Flipr to **Eco Mode** (2 measures/day) or Sleep (0 measure/day) via the integration options. The official gateway handles the cloud sync, while Home Assistant reads the data locally without draining the battery.

---

### 📊 Available Sensors and Controls
| Entity | Unit / Type | Description |
| :--- | :--- | :--- |
| 💧 **pH** | pH | Calculated pH (Nernst + Temp Compensation). |
| ⚡ **Redox / ORP** | mV | Oxidation-Reduction Potential. |
| 🌡️ **Temperature** | °C | Precise water temperature. |
| 🌫️ **Estimated Free Chlorine**| ppm | Estimated free chlorine level (FC). |
| 🧪 **Active Chlorine** | mg/L | Estimated actual disinfection power (HOCl). |
| ⚖️ **Langelier Index** | LSI | Water balance indicator (Corrosive, Balanced, or Scaling). |
| 🎯 **Equilibrium pH** | pH | Target ideal pH calculated via the Taylor Balance. |
| 🔋 **Battery** | % and mV | Charge level (%) and raw battery voltage. |
| 📶 **RSSI Signal** | dBm | Real-time received Bluetooth signal strength. |
| 🔵 **Bluetooth State** | Status | Detailed connection state (Connected, Sleeping, Error...). |
| 🔄 **Sync Mode** | Diagnostic | Current probe mode read from the BLE frame (Eco, Boost...). |
| ⏱️ **Next Analysis** | Timestamp | Estimated time of the next data poll. |
| 🚀 **New Analysis** | Button | **Trigger an instant analysis (~60s).** |
| ⏸️ **Auto Analyses** | Switch | Enable/Disable automatic polling (Pause Mode). |

> 🛠️ **Diagnostic**: The integration also exposes advanced sensors (raw pH in mV, factory formula pH, raw hex frame, and binary alert statuses).

---

### 🧪 Chemical Expertise: Professional-Grade Analysis

👉 No need to understand these calculations: everything is automated in Home Assistant.

<details>
<summary>🔬 View scientific details</summary>

#### 1. Active Chlorine (The true disinfection power) 🧂
The ORP (Redox) probe does not measure the quantity of chlorine (mg/L), but the **disinfection strength** of the water. This power drops significantly as the pH rises. Flipr Local cross-references your ORP and pH in real-time to provide an estimate of the **Active Chlorine** level, the only true indicator to know if your water is properly sanitizing.

#### 2. Water Balance: Langelier Saturation Index & Taylor Balance ⚖️
The Langelier Saturation Index (LSI) is the essential companion to the **Taylor Balance**. It determines if your water is:
* **Corrosive (LSI < -0.3)**: The water is eating away at your seals, liner, and metals.
* **Balanced (LSI between -0.3 and +0.3)**: Perfect water.
* **Scaling (LSI > +0.3)**: Risk of calcium deposits.

Enter your Alkalinity (TAC), Hardness (TH), and TDS in the options, and Home Assistant will calculate your balance live based on the temperature read by the Flipr!

> **Diagnostic**: The integration also exposes the raw pH (mV), the factory-calculated pH, the full hex frame, and the timestamp of the last measurement.

</details>


### 🎯 A Note on Measurement Accuracy
The values displayed in Home Assistant may differ slightly from the official Flipr app.

Flipr Local enables "high-precision" calibration. Unlike the mobile app, which uses fixed values, our integration allows you to enter the exact value of your buffer solution (pH 7.02, 4.01, etc.) adjusted for temperature during calibration. This scientific rigor may create a slight discrepancy, indicating a measurement that is closer to the reality of your pool. 🔬

---

## 🚀 Configuration
1. Go to **Settings** > **Devices & Services**.
2. The integration should automatically discover your Flipr if your Bluetooth adapter/antenna is in range.
3. Click **Add Integration** and search for **Flipr Local**.
4. Follow the on-screen instructions to define the treatment type (Chlorine, Bromine) and the calibration/offset of your probes.

### ⚙️ Options, Calibrations, and Alerts
Once the device is added, you can click on **Configure** ⚙️ to:
* Adjust your calibration solution values (pH 4, pH 7, ORP).
* Modify your water parameters (TAC, TH, TDS, Stabilizer) via the dashboard.
* Define your **custom alert thresholds** (Min/Max pH, Min/Max ORP, etc.) to trigger your own automations.

---

### 🐛 Troubleshooting

<details>
<summary>⚠️ View common issues</summary>
  
* **Frequent Bluetooth errors**: The integration automatically handles connection retries. If the sensor shows `Signal Lost`, the Flipr is out of range. Move your antenna closer or [install an ESPHome Bluetooth Proxy](https://esphome.github.io/bluetooth-proxies/) as close to the pool as possible (only requires an ESP32 (~10€) and a USB charger).
* **Free and Active Chlorine show "Unknown"**: If you selected "Bromine" in the options, this is normal behavior. Bromine is not calculated the same way as chlorine. Rely on the ORP (Redox) probe value.
* **I don't use stabilizer**: Simply set the `CyA (Stabilizer)` entity to `0`. The chemical calculation will adapt automatically.

</details>

---

### 🛠️ Hardware Rescue:

<details>
<summary>🔧 View the complete procedure</summary>

If your Flipr probes are dead, you can replace them yourself!

**Hardware required:**
1. Replacement probes (pH and ORP) with a BNC connector (Recommended dimensions: **12 mm diameter, 15-16 cm long**).
2. Two adapter cables (**Pigtails**): `Right-angle MCX Male (90°) to BNC Female`. *The right-angle connector is essential to be able to close the Flipr cover.*

**Quick Procedure:**
Remove the old probes, clean the white base. Plug the MCX adapters into the motherboard (`PH` and `ORP` ports). Pass the new probes through the original holes (12 mm), connect them to the BNC cables. Calibrate via Home Assistant, and you're good to go!

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
