[![Home Assistant Configuration](https://github.com/ohadbenita/homeassistant/actions/workflows/validate_hass_configuration.yml/badge.svg)](https://github.com/ohadbenita/homeassistant/actions/workflows/validate_hass_configuration.yml)
[![GitHub last commit](https://img.shields.io/github/last-commit/ohadbenita/homeassistant.svg?style=plasticr)](https://github.com/ohadbenita/homeassistant/commits/master)
[![Commits Year](https://img.shields.io/github/commit-activity/y/ohadbenita/homeassistant.svg?style=plasticr)](https://github.com/ohadbenita/homeassistant/commits/master)
[![GitHub stars](https://img.shields.io/github/stars/ohadbenita/homeassistant.svg?style=plasticr)](https://github.com/ohadbenita/homeassistant/stargazers)
![Home Assistant Release](https://img.shields.io/github/v/release/home-assistant/core?label=Home%20Assistant&logo=home-assistant&sort=semver)
[![Discord](https://img.shields.io/discord/702447199681904720.svg?style=plasticr)](https://discord.gg/ayZ3Kkg)


# Ohadbenita's Home Assistant Configuration

Welcome to my Home Assistant configuration repository! This repo contains my personal setup and configurations for Home Assistant, tailored for an efficient smart home experience with a focus on mobile devices using Lovelace UI.

## Introduction

This repository provides a comprehensive setup of Home Assistant, including various automations, integrations, and customizations to enhance your smart home. Feel free to explore, use, and modify the configurations to suit your own needs. Contributions and suggestions are always welcome!

## Features

- **Lovelace UI**: Customized for mobile devices.
- **Automations**: Lighting, climate control, and security automations.
- **Integrations**: Seamless integration with popular smart home devices and services.
- **Custom Components**: Extended functionality with custom components and scripts.
- **Themes**: Personalized themes for an enhanced user experience.

## Installation

To use this configuration, follow these steps:

1. **Clone the Repository**:
   ```sh
   git clone https://github.com/ohadbenita/homeassistant.git
   cd homeassistant
   ```

2. **Install Home Assistant**:
   Follow the [Home Assistant installation guide](https://www.home-assistant.io/getting-started/) for your specific platform.

3. **Copy Configuration Files**:
   Copy the configuration files from this repository to your Home Assistant configuration directory.

4. **Restart Home Assistant**:
   Restart Home Assistant to apply the new configurations.

## Usage

After setting up Home Assistant with this configuration, you can access the Lovelace UI through your mobile device. Customize the dashboard and automations as needed to fit your smart home setup.

# Automations Overview

This Home Assistant setup includes a variety of automations and packages that allow for comprehensive home automation. Below is an overview of the key automations, features, and configurations available in this setup.

## Key Automations and Features

### 1. Room-Specific Automations

Each room in the house has its own dedicated automation file in the `packages` directory:
- **[adi_room.yaml](./packages/adi_room.yaml)**: Manages automations specific to Adi's room.
- **[ella_room.yaml](./packages/ella_room.yaml)**: Handles automations for Ella's room.
- **[roi_room.yaml](./packages/roi_room.yaml)**: Manages Roi's room settings and automations.
- **[study_room.yaml](./packages/study_room.yaml)**: Automates the study room, including lighting and presence detection.
- **[master_bedroom.yaml](./packages/master_bedroom.yaml)**: Contains automations for the master bedroom.
- **[living_room.yaml](./packages/living_room.yaml)**: Handles automations for lighting, entertainment, and climate control in the living room.
- **[kitchen.yaml](./packages/kitchen.yaml)**: Manages automations for the kitchen area.
- **[dining_room.yaml](./packages/dining_room.yaml)**: Automates the dining room lighting and environment.
- **[guest_bathroom.yaml](./packages/guest_bathroom.yaml)**: Controls automations for the guest bathroom.
- **[kids_bathroom.yaml](./packages/kids_bathroom.yaml)**: Automations for the kids' bathroom.
- **[basement.yaml](./packages/basement.yaml)**: Manages automations for the basement, including lighting and security.

### 2. Security Automations
- **[security.yaml](./packages/security.yaml)**: This file includes automations for monitoring and securing the home, including motion sensors and alerts.

### 3. Awtrix Integration
- **[awtrix.yaml](./packages/awtrix.yaml)**: Integrates Awtrix with Home Assistant, allowing for custom notifications and settings changes through the Awtrix display.
  - Awtrix GitHub repository: [Awtrix on GitHub](https://github.com/awtrix/Awtrix)

### 4. Notification Automations
- **[notification.yaml](./notification.yaml)**: Handles notifications for various events, such as when a sensor detects motion or when certain devices turn on or off.

### 5. Yard and Outdoor Automations
- **[yard.yaml](./packages/yard.yaml)**: Automates outdoor lighting and other yard-related tasks.

### 6. Presence Detection
- **[presence.yaml](./packages/presence.yaml)**: Manages presence detection using multiple methods (likely via phones or other sensors) to adjust home behavior based on who is present.

### 7. Red Alert Automations
- **[red_alert.yaml](./packages/red_alert.yaml)**: Likely an emergency alert system, triggering actions during urgent situations.

### 8. Scripted Actions
- **[turn_everything_off.yaml](./scripts/turn_everything_off.yaml)**: A script to turn off all devices in the home.
- **[alexa_actionable_notifications.yaml](./scripts/alexa_actionable_notifications.yaml)**: Manages actionable notifications through Alexa.

## Configuration Files
- **[configuration.yaml](./configuration.yaml)**: The main configuration file for Home Assistant, pulling together all the integrations and settings.
- **[secrets-redacted.yaml](./secrets-redacted.yaml)**: A redacted version of the secrets file, likely used to store sensitive credentials.
- **[group.yaml](./group.yaml)**: Defines various groups of entities for easier management and automation.
- **[input_boolean.yaml](./input_boolean.yaml)**: Defines toggle switches for certain automation conditions.
- **[input_text.yaml](./input_text.yaml)**: Allows for dynamic text input, useful in more complex automations.

- This setup is designed to be modular, allowing for easy customization and expansion by adding new packages and automations to the appropriate room or function.

## Contributions

Contributions are welcome! If you have any suggestions, bug reports, or feature requests, please open an issue or submit a pull request.

## Community

Join our [community on Discord](https://discord.gg/ayZ3Kkg) to discuss Home Assistant configurations, share ideas, and get help

## Support

If you find this configuration helpful, consider supporting my work by buying me a coffee:

[![Buy Me A Coffee](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/OeZ1R5f)

---

Thank you for visiting my Home Assistant configuration repository. Enjoy automating your home!

## License

This project is licensed under the Apache-2.0 License - see the [LICENSE](LICENSE) file for details.
