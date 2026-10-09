# Home Assistant Configuration

[![Home Assistant Configuration](https://github.com/ohadbenita/homeassistant/actions/workflows/validate_hass_configuration.yml/badge.svg)](https://github.com/ohadbenita/homeassistant/actions/workflows/validate_hass_configuration.yml)
[![GitHub last commit](https://img.shields.io/github/last-commit/ohadbenita/homeassistant.svg?style=plasticr)](https://github.com/ohadbenita/homeassistant/commits/master)
[![Commits Year](https://img.shields.io/github/commit-activity/y/ohadbenita/homeassistant.svg?style=plasticr)](https://github.com/ohadbenita/homeassistant/commits/master)
![Home Assistant Release](https://img.shields.io/github/v/release/home-assistant/core?label=Home%20Assistant&logo=home-assistant&sort=semver)

This repository contains the Home Assistant configuration for a family home. The goal is to make the home respond to context—who is home, what equipment is doing, and what sensors see—and to send a useful alert when something needs attention. The configuration brings together room controls, safety routines, energy tracking, and camera analysis in focused YAML packages.

## What it does

### Room-by-room control

Files under [packages](./packages/) define automations and helpers for individual rooms and systems. Examples include:

- **Presence-aware comfort and lighting:** [study room](./packages/study_room.yaml), [living room](./packages/living_room.yaml), [bedrooms](./packages/ella_room.yaml), [kids' rooms](./packages/adi_room.yaml), and other room packages use motion, presence, schedules, and manual controls to manage lights, covers, fans, and air conditioning.
- **Laundry and household routines:** [chore statistics](./packages/chore_stats.yaml) counts dishwasher and washing-machine cycles. The [kids' bathroom](./packages/kids_bathroom.yaml) package announces a completed washing cycle.
- **Whole-home helpers:** [groups](./group.yaml), [input booleans](./input_boolean.yaml), and [templates](./custom_templates/) support shared controls and automation logic.

Room files can include more than one feature; for example, the study-room package controls lights, air conditioning, covers, and printer-related button actions.

### A few end-to-end examples

- **A possible kitchen leak:** the under-sink leak sensor triggers a Telegram alert. The automation reports the event; it does not close a water valve.
- **Laundry at sunset:** when outdoor humidity is above 65%, Home Assistant asks the camera-analysis service whether laundry is still on the rack. A separate night alert checks the laundry detector and humidity before notifying.
- **Irrigation check:** after the trees-and-bushes irrigation switches have been on for two minutes, the camera-analysis service checks for visible leakage. Home Assistant sends an alert and a camera snapshot when the result confidence is at least 0.8.
- **Away-mode entrance alert:** when the main entrance camera detects a person while the alarm is armed away, Home Assistant saves a snapshot and sends it with a Telegram alert.
- **Solar fault alert:** if the SolarEdge inverter status stays unavailable for 10 minutes, Home Assistant notifies the configured Telegram and mobile-app targets.
- **Appliance cycle tracking:** the dishwasher counter increments after its active sensor stays off for 44 minutes; the washing-machine counter waits for a high-power start and sustained idle before counting a completed cycle.

### Safety, security, and device health

- [Security](./packages/security.yaml) coordinates door and window state, locks, and Away Mode behavior.
- [Outdoor and yard controls](./packages/yard.yaml) and [balcony controls](./packages/balcony.yaml) use motion and person detection for lights, with timed shutoff behavior.
- [Leak-related automations](./packages/yard.yaml) and [boiler monitoring](./packages/boiler_leak.yaml) send alerts when their configured conditions are met.
- [Zigbee sensor monitoring](./packages/zigbee_sensor_monitoring/) watches selected trigger sensors for unavailable states and reports recovery.
- [Home Assistant health automations](./packages/ha.yaml) cover firmware update prompts, Synology drive/security alerts, and other system notifications.

The alert examples and thresholds are defined in the YAML files; actual behavior depends on the related integrations and entities being available in the Home Assistant instance.

### Energy and solar

[Energy monitoring](./packages/energy.yaml) combines SolarEdge production with measured consumption from Shelly and other energy sensors. It defines cumulative consumption and return-to-grid sensors, compares monthly production with expected values, estimates solar income using configurable rates, and tracks a camera-based panel-cleanliness assessment.

### Camera analysis

The [Generative AI service](./generative-ai/) is a Flask application packaged with its [Dockerfile](./generative-ai/Dockerfile). It calls Amazon Bedrock to analyze selected Home Assistant camera images and writes results back to Home Assistant. The configured use cases include:

- Detecting laundry on the clothes rack.
- Reading the gas heater display.
- Study-room and entrance camera analysis.
- Checking the LPG auto-switcher, visible irrigation leakage, and solar-panel cleanliness.

Home Assistant calls the service through REST commands in the relevant packages. In practice, the service adds a visual signal to normal automations: a camera result becomes a Home Assistant entity, and package logic decides whether it should trigger an alert. The application code and container build files are in this repository; service deployment and its credentials must be configured in the environment where it runs.

### Notifications and scripts

Notification actions are defined alongside the automations that use them. They target instance integrations such as Telegram and the Home Assistant mobile app; configure those integrations and entities in Home Assistant.

Reusable scripts are in [scripts](./scripts/):

- [turn_everything_off.yaml](./scripts/turn_everything_off.yaml) provides a whole-home shutdown action.
- [alexa_actionable_notifications.yaml](./scripts/alexa_actionable_notifications.yaml) handles Alexa prompts and responses.
- [download_latest_timelapse.sh](./scripts/download_latest_timelapse.sh) fetches the newest 3D-printer MP4 timelapse from Moonraker into Home Assistant's www directory.

## Repository layout

| Path | Purpose |
| --- | --- |
| [configuration.yaml](./configuration.yaml) | Main entry point; loads packages, automations, scripts, groups, helpers, scenes, and notifications. |
| [packages/](./packages/) | Feature configuration, mostly grouped by room or system. |
| [automations/](./automations/) | Automations kept outside packages, including shared security and stair-light behavior. |
| [custom_templates/](./custom_templates/) | Jinja templates shared by the configuration. |
| [scripts/](./scripts/) | Home Assistant scripts and utility scripts. |
| [generative-ai/](./generative-ai/) | Camera-analysis application and container build files. |
| [docs/](./docs/) | Setup notes, including the [Raspberry Pi USB camera to RTSP guide](./docs/rpi-mediamtx-usb-camera.md). |
| [.github/workflows/](./.github/workflows/) | Linting, Home Assistant configuration validation, and optional live-sync workflow. |

## Configuration and secrets

The main configuration loads packages from packages/ and automations from automations/. It also enables Home Assistant's default integrations, TOTP MFA, a 30-day recorder retention period, and an allowlist for snapshot files in /config/www/snapshots.

This is a configuration for a specific home, not a drop-in starter: packages refer to the installation's entity IDs, hardware, integrations, and network services. Review those references when adapting it to another Home Assistant instance.

The YAML files also use instance-specific endpoints and values stored as Home Assistant secrets. Supply a private secrets.yaml for the target instance; [secrets-redacted.yaml](./secrets-redacted.yaml) shows example secret names with placeholder values and must not be used as real credentials. Integrations such as MQTT, Telegram, SolarEdge, Shelly, cameras, Alexa, and mobile-app notifications must exist and expose the entities referenced by the packages.

## Validation and live sync

The [GitHub Actions workflow](./.github/workflows/validate_hass_configuration.yml) runs YAML, JSON, and Markdown linting, then checks the Home Assistant configuration with the current stable Home Assistant container. On a push to master, it can also request a live sync when the HA_URL and HA_TOKEN repository secrets are configured.

The live-sync automation and status sensors are defined in [packages/github_sync.yaml](./packages/github_sync.yaml); the sync script is [scripts/sync_from_git.sh](./scripts/sync_from_git.sh). It fetches the configured branch, checks the candidate configuration before applying it, and reports sync status in www/github_sync_status.json. The workflow waits for the live instance to report the commit it requested.

## Additional guide

- [Raspberry Pi USB camera to RTSP with MediaMTX](./docs/rpi-mediamtx-usb-camera.md)
