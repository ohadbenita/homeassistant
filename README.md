# My Home Assistant Configuration

[![Home Assistant Configuration](https://github.com/ohadbenita/homeassistant/actions/workflows/validate_hass_configuration.yml/badge.svg)](https://github.com/ohadbenita/homeassistant/actions/workflows/validate_hass_configuration.yml)
[![GitHub last commit](https://img.shields.io/github/last-commit/ohadbenita/homeassistant.svg?style=plasticr)](https://github.com/ohadbenita/homeassistant/commits/master)
[![Commits Year](https://img.shields.io/github/commit-activity/y/ohadbenita/homeassistant.svg?style=plasticr)](https://github.com/ohadbenita/homeassistant/commits/master)
![Home Assistant Release](https://img.shields.io/github/v/release/home-assistant/core?label=Home%20Assistant&logo=home-assistant&sort=semver)

---

## Overview

This repo powers my family’s smart home using [**Home Assistant**](https://www.home-assistant.io/). It includes:

- Automations for every room.
- Alerts for device health, firmware, and network outages.
- Outdoor lighting and laundry checks.
- Energy monitoring tied into solar production.
- A generative AI service for camera-based detection.

---

## Room & Daily-Life Automations

Every room has a dedicated package, so automations are isolated and easy to manage.

- **Example:** When someone enters the [study room](./packages/study_room.yaml), the lights turn on automatically, but only if it’s after sunset. If the 3D printer is active, a progress sensor updates the dashboard so we know when a print is nearing completion.
- **Example:** In the [kids’ bathroom](./packages/kids_bathroom.yaml), a motion sensor turns on the mirror light at night, but only dimly, to avoid waking them fully.
- **Example:** [Kitchen automations](./packages/kitchen.yaml) ensure that if a leak sensor triggers, the under-sink valve closes and a Telegram alert is sent immediately.

This modular design makes it easy to expand or tweak just one area of the home.

---

## System Health & Security

The [ha.yaml](https://github.com/ohadbenita/homeassistant/blob/master/packages/ha.yaml) package ensures Home Assistant and critical devices stay reliable:

- **Example:** Every time HA restarts, I get a push notification on my phone saying *“Home Assistant is online – version x.y.z”*.
- **Example:** If Zigbee sensors (via Z2M) go offline, I get a Telegram alert naming the exact device.
- **Example:** If a new HA release is out, HA messages me with the version number and link to release notes, and only once per version.
- **Example:** When Shelly devices have firmware updates available, HA lets me trigger the update directly from Telegram, or snooze it until the weekend.

[security.yaml](./packages/security.yaml) adds intrusion detection — if motion is detected when the house is in *Away Mode*, it triggers sirens and notifies everyone.

---

## Outdoor & Yard Control

The [yard.yaml](https://github.com/ohadbenita/homeassistant/blob/master/packages/yard.yaml) file coordinates multiple outdoor devices:

- **Example:** At 23:00, roof floodlights turn off automatically unless motion is still detected.
- **Example:** If someone walks near the clinic entrance at night, the floodlight and path lights turn on for 5 minutes.
- **Example:** If laundry is still hanging outside an hour after sunset *and humidity is high*, HA snaps a photo of the clothesline, sends it via Telegram, and prompts us to bring laundry inside.

The [balcony.yaml](./packages/balcony.yaml) handles pergola lighting:

- **Example:** If the stairs’ motion sensor trips after sunset, the pergola fan light turns on automatically for safe passage.

---

## Energy Monitoring

The [energy.yaml](https://github.com/ohadbenita/homeassistant/blob/master/packages/energy.yaml) package merges **Shelly smart switch data** with **SolarEdge production** to calculate:

- **Example:** Current net consumption vs. solar generation, updated every minute.
- **Example:** If solar production exceeds home usage, a “Return to Grid” counter ticks up, letting us track how much we’re selling back.
- **Example:** Monthly energy income in ILS (₪) is calculated automatically and shown on the dashboard.

---

## Notifications

Multi-channel notifications make sure issues don’t go unnoticed:

- **Example:** If my son’s iPhone storage drops below 5%, HA sends a push to his device saying exactly how much storage is left.
- **Example:** If WhatsApp’s API service becomes unavailable (monitored via REST checks), I get a Telegram alert with the API URL that failed.
- **Example:** If any Zigbee door sensor reports low battery, HA creates a persistent notification listing the affected devices.

See [notification.yaml](./notification.yaml).

---

## Helpers & Templates

- [configuration.yaml](https://github.com/ohadbenita/homeassistant/blob/master/configuration.yaml) → loads all packages, groups, scenes, and scripts.
- [group.yaml](https://github.com/ohadbenita/homeassistant/blob/master/group.yaml) → groups like `all_lights` and `all_ac` allow whole-house actions.
- [input_boolean.yaml](https://github.com/ohadbenita/homeassistant/blob/master/input_boolean.yaml) → toggles like *Away Mode* and *Skip Firmware Updates*.
- [availability_template.jinja](https://github.com/ohadbenita/homeassistant/blob/master/custom_templates/availability_template.jinja) → ensures entity availability before automations act on them.

---

## Generative AI Vision Service

The [Generative AI app](https://github.com/ohadbenita/homeassistant/blob/master/generative-ai/app.py), containerized via this [Dockerfile](https://github.com/ohadbenita/homeassistant/blob/master/generative-ai/Dockerfile), uses **Amazon Bedrock** for camera analysis.

- **Example:** HA asks the AI server *“Is laundry on the clothes rack?”* → If yes, a binary sensor in HA turns `on`, triggering laundry alerts.
- **Example:** For the gas heater, AI parses the **temperature digits** and the **status LEDs**. If the heater is “on” but the green LED is missing, HA notifies us of a malfunction.
- **Example:** Study room camera images are analyzed for human presence, allowing lights to follow real occupancy even if motion sensors miss it.

---

## Scripts

- [turn_everything_off.yaml](./scripts/turn_everything_off.yaml) → “panic button” to turn off all lights and devices at once.
- [alexa_actionable_notifications.yaml](./scripts/alexa_actionable_notifications.yaml) → lets Alexa ask *“Do you want me to turn off the lights?”* and process yes/no responses.
- [download_latest_timelapse.sh](https://github.com/ohadbenita/homeassistant/blob/master/scripts/download_latest_timelapse.sh) → grabs the latest 3D printer timelapse video and saves it into HA’s `/www` folder for quick playback.

---
