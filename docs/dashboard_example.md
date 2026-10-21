[![Français](https://img.shields.io/badge/Langue-Fran%C3%A7ais-blue)](dashboard_example.fr.md) [![English](https://img.shields.io/badge/Language-English-red)](#)
[← Back to README](README.md)

# 📊 Flipr Local - Dashboard Example

This page gives the YAML of the dashboard shown in the README, so you can copy it into your own Home Assistant. It is made of **two cards** placed one after the other in a *Sections* view. 💡

<p align="center">
  <img src="screenshots/dashboard_overview.png" width="800" alt="Dashboard overview">
</p>

---

## 1. 📦 Prerequisites

The cards rely on three custom cards, all available through **HACS** (Frontend):

| Card | Used for |
|---|---|
| [`mini-graph-card`](https://github.com/kalkih/mini-graph-card) | The 24 h graphs with colour thresholds |
| [`mushroom`](https://github.com/piitaya/lovelace-mushroom) | The badges (battery, last update, time) |
| [`card-mod`](https://github.com/thomasloven/lovelace-card-mod) | Keeps the badges on a single line |

> 💡 The layout is designed for a **Sections** view. In another view type (Masonry, Panel), the cards still work: simply remove the final `grid_options` block of the graphs card.

---

## 2. ✏️ Adapt the entity names

The YAML below uses the entity IDs of a **Flipr AnalysR 3** (`sensor.flipr_analysr_3_*`). **Your IDs depend on the name of your Flipr device in Home Assistant**, so replace them with yours:

| In the YAML | Entity |
|---|---|
| `sensor.flipr_analysr_3_temperature` | Temperature |
| `sensor.flipr_analysr_3_ph` | pH |
| `sensor.flipr_analysr_3_orp_redox` | ORP (Redox) |
| `sensor.flipr_analysr_3_batterie` | Battery (`_battery` with an English interface) |

> 💡 The exact IDs are in **Settings** > **Devices & services** > **Flipr** > *entities*. The easiest way is a *Find & Replace* of `flipr_analysr_3` with your own prefix in the editor.

---

## 3. 🚀 Add the cards

In your **Sections** view, click ⋮ > **Edit dashboard**, then, inside the section of your choice:

1. Click **+ Add card**, scroll down and choose **Manual**, paste the YAML of step 4 (title and badges), then **Save**.
2. Repeat with the YAML of step 5 (graphs).

---

## 4. 🏷️ Title and badges

Heading with three badges: **battery level**, **time elapsed since the last analysis** and **time of the last analysis**.

```yaml
type: heading
icon: mdi:pool-thermometer
heading: Flipr Connect Local
heading_style: title
badges:
  - type: custom:mushroom-template-badge
    icon: mdi:battery
    content: >-
      {{ "{:,.0f}".format(states('sensor.flipr_analysr_3_batterie') | float) |
      replace(',', ' ') }} %
    card_mod:
      style: |
        :host {
          white-space: nowrap;
        }
  - type: custom:mushroom-template-badge
    icon: mdi:update
    content: >-
      {% set last_up = states.sensor.flipr_analysr_3_temperature.last_updated
      %} {% if last_up is not none %}
        {% set diff = (as_timestamp(last_up) - as_timestamp(now())) | abs | int %}
        {% set heures = (diff // 3600) %}
        {% set minutes = ((diff % 3600) // 60) %}
        {%- if heures > 0 -%}
          Il y a {{ heures }} h
        {%- else -%}
          Il y a {{ minutes }} min
        {%- endif -%}
      {% else %}
        Inconnu
      {% endif %}
    card_mod:
      style: |
        :host {
          white-space: nowrap;
        }
  - type: custom:mushroom-template-badge
    icon: mdi:clock-outline
    content: >-
      {% set last_up = states.sensor.flipr_analysr_3_temperature.last_updated
      %} {% if last_up is not none %}
        {{ as_timestamp(last_up) | timestamp_custom('%Hh%M') }}
      {% else %}
        --h--
      {% endif %}
    card_mod:
      style: |
        :host {
          white-space: nowrap;
        }
```

---

## 5. 📈 Graphs

Three 24 h graphs (temperature, pH, ORP) with colour thresholds, taking the full width of the section. The **min / max** values are displayed (`extrema: true`).

```yaml
square: false
type: grid
columns: 2
cards:
  - type: custom:mini-graph-card
    cache: false
    decimals: 2
    entities:
      - entity: sensor.flipr_analysr_3_temperature
        name: 🌡️ Temperature
    color_thresholds:
      - value: 20
        color: '#00AEEF'
      - value: 25
        color: '#00E4D0'
      - value: 27
        color: '#32CD32'
      - value: 29.5
        color: '#32CD32'
      - value: 31
        color: '#FF8000'
      - value: 32.5
        color: '#FF0000'
    color_thresholds_transition: smooth
    smoothing: true
    points_per_hour: 1
    hours_to_show: 24
    line_width: 5
    show:
      fill: fade
      graph: line
      extrema: true
      legend: false
    locale: fr
    hour24: true
    icon: mdi:thermometer-water
  - type: custom:mini-graph-card
    cache: false
    decimals: 2
    entities:
      - entity: sensor.flipr_analysr_3_ph
        name: 💧 pH
    color_thresholds:
      - value: 6.6
        color: '#FF0000'
      - value: 6.9
        color: '#FF8000'
      - value: 7
        color: '#32CD32'
      - value: 7.2
        color: '#32CD32'
      - value: 7.35
        color: '#FF8000'
      - value: 7.6
        color: '#FF0000'
    color_thresholds_transition: smooth
    smoothing: true
    points_per_hour: 1
    hours_to_show: 24
    line_width: 5
    show:
      fill: fade
      graph: line
      extrema: true
      legend: false
    locale: fr
    hour24: true
    icon: mdi:ph
  - type: custom:mini-graph-card
    cache: false
    entities:
      - entity: sensor.flipr_analysr_3_orp_redox
        name: 💧 ORP
    color_thresholds:
      - value: 550
        color: '#FF0000'
      - value: 650
        color: '#FF8000'
      - value: 680
        color: '#32CD32'
      - value: 760
        color: '#32CD32'
      - value: 800
        color: '#FF8000'
      - value: 850
        color: '#FF0000'
    color_thresholds_transition: smooth
    smoothing: true
    points_per_hour: 1
    hours_to_show: 24
    line_width: 5
    show:
      fill: fade
      graph: line
      extrema: true
      legend: false
    locale: fr
    hour24: true
    icon: mdi:flask-outline
grid_options:
  columns: full
```

---

## 6. 📱 Variant without min / max

For smaller graphs (narrow section, phone), use the same YAML as step 5 and change **`extrema: true`** into **`extrema: false`** (3 occurrences, one per graph).

---

## 7. 🎨 Customization

* **Colour thresholds** (`color_thresholds`): each `value` is the point where the line starts to take the given colour. The green zones match an ideal pool (pH 7.0 – 7.2, ORP 680 – 760 mV, temperature 27 – 29.5 °C). Adapt them to your own targets.
* **Time window**: change `hours_to_show` (e.g. `72` for three days) and `points_per_hour` to smooth or refine the curve.
* **Language**: `locale: fr` controls the number format (decimal comma). Use `locale: en` for a decimal point.
* **Badge text**: the *"Il y a … h / min"* and *"Inconnu"* wording is in French in the template; translate it if needed.
* **Heading**: change `heading: Flipr Connect Local` to the name you want.
