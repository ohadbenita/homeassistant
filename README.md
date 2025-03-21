# My Home Assistant Configuration

[![Home Assistant Configuration](https://github.com/ohadbenita/homeassistant/actions/workflows/validate_hass_configuration.yml/badge.svg)](https://github.com/ohadbenita/homeassistant/actions/workflows/validate_hass_configuration.yml)
[![GitHub last commit](https://img.shields.io/github/last-commit/ohadbenita/homeassistant.svg?style=plasticr)](https://github.com/ohadbenita/homeassistant/commits/master)
[![Commits Year](https://img.shields.io/github/commit-activity/y/ohadbenita/homeassistant.svg?style=plasticr)](https://github.com/ohadbenita/homeassistant/commits/master)
[![GitHub stars](https://img.shields.io/github/stars/ohadbenita/homeassistant.svg?style=plasticr)](https://github.com/ohadbenita/homeassistant/stargazers)
![Home Assistant Release](https://img.shields.io/github/v/release/home-assistant/core?label=Home%20Assistant&logo=home-assistant&sort=semver)
[![Discord](https://img.shields.io/discord/702447199681904720.svg?style=plasticr)](https://discord.gg/ayZ3Kkg)

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

## Home Assistant Automations Overview

This Home Assistant setup includes a variety of automations and packages that allow for comprehensive home automation. Below is an overview of the key automations, features, and configurations available in this setup.

### Key Automations and Features

#### 1. Room-Specific Automations

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

#### 2. Security Automations

- **[security.yaml](./packages/security.yaml)**: This file includes automations for monitoring and securing the home, including motion sensors and alerts.

#### 3. Awtrix Integration

- **[awtrix.yaml](./packages/awtrix.yaml)**: Integrates Awtrix with Home Assistant, allowing for custom notifications and settings changes through the Awtrix display.
  - Awtrix GitHub repository: [Awtrix on GitHub](https://github.com/awtrix/Awtrix)

#### 4. Notification Automations

- **[notification.yaml](./notification.yaml)**: Handles notifications for various events, such as when a sensor detects motion or when certain devices turn on or off.

#### 5. Yard and Outdoor Automations

- **[yard.yaml](./packages/yard.yaml)**: Automates outdoor lighting and other yard-related tasks.

#### 6. Presence Detection

- **[presence.yaml](./packages/presence.yaml)**: Manages presence detection using multiple methods (likely via phones or other sensors) to adjust home behavior based on who is present.

### 7. Red Alert Automations

- **[red_alert.yaml](./packages/red_alert.yaml)**: An emergency alert system, triggering actions during urgent situations.

### 8. Scripted Actions

- **[turn_everything_off.yaml](./scripts/turn_everything_off.yaml)**: A script to turn off all devices in the home.
- **[alexa_actionable_notifications.yaml](./scripts/alexa_actionable_notifications.yaml)**: Manages actionable notifications through Alexa.

### Configuration Files

- **[configuration.yaml](./configuration.yaml)**: The main configuration file for Home Assistant, pulling together all the integrations and settings.
- **[secrets-redacted.yaml](./secrets-redacted.yaml)**: A redacted version of the secrets file, likely used to store sensitive credentials.
- **[group.yaml](./group.yaml)**: Defines various groups of entities for easier management and automation.
- **[input_boolean.yaml](./input_boolean.yaml)**: Defines toggle switches for certain automation conditions.
- **[input_text.yaml](./input_text.yaml)**: Allows for dynamic text input, useful in more complex automations.

This setup is designed to be modular, allowing for easy customization and expansion by adding new packages and automations to the appropriate room or function.

## Generative AI server

- The generative AI server is a Docker-wrapped Flask web service that exposes camera image analysis and reporting of data identified by an LLM of your choice back as a Home Assistant entity.
- The web service uses Amazon Bedrock as the platform to invoke the model, which is configurable according to your needs.
- Keep in mind that the current implementation is designed to my needs, but changing the prompt and entities to one's needs is relatively simple.

### How-To install

1. Change the [app.py](./generative-ai/app.py) code to expose endpoints to your needs.
2. Build and deploy the docker image (See [Dockerfile](./generative-ai/Dockerfile)) by running `docker build -t camera-analysis .`
3. Configure an IAM user with permissions to invoke the [AWS Bedrock](https://aws.amazon.com/bedrock/) model you chose. Keep in mind the cost could be steep so use this service wisely.
4. Configure the required environment variables for the app service.
5. Deploy the container using Docker CLI or Docker compose:

```yaml
  gen_ai_server:
    image: hass-generative-ai:latest
    container_name: hass-gen-ai-server
    restart: unless-stopped
    network_mode: bridge
    ports:
      - "6543:5000"
    environment:
      - HA_BASE_URL=${HA_BASE_URL}
      - HA_TOKEN=${HA_TOKEN}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_DEFAULT_REGION=US-EAST-1
      - CLOTHES_RACK_CAMERA_ENTITY_ID=${CLOTHES_RACK_CAMERA_ENTITY_ID}
      - CLOTHES_RACK_TARGET_ENTITY_ID=${CLOTHES_RACK_TARGET_ENTITY_ID}
      - GAS_HEATER_CAMERA_ENTITY_ID=${GAS_HEATER_CAMERA_ENTITY_ID}
      - GAS_HEATER_TARGET_ENTITY_ID=${GAS_HEATER_TARGET_ENTITY_ID}
```
6. Configure Home Assistant to call the web service using REST command:

```yaml
  - alias: "Alert if water heater is out of order"
    id: cloak_room_gas_water_heater_check
    initial_state: true
    trigger:
      platform: sun
      event: sunset
      offset: '01:00:00'

    condition:
      - condition: template
        value_template: >-
          {{ not (state_attr('sensor.water_heater', 'is_out_of_order') == 'off' and is_state('sensor.water_heater', '45')) }}

    action:
      - action: camera.snapshot
        data:
          entity_id: camera.gas_heater_cam_gas_heater_esp32_cam
          filename: "/config/www/snapshots/gas_heater_cam_gas_heater_esp32_cam_snapshot.jpg"

      - delay: '00:00:02'

      - action: notify.ohad_telegram
        data:
          title: "Alert: Water heater malfunction"
          message: "Please check the heater display"
          data:
            photo:
              - file: "/config/www/snapshots/gas_heater_cam_gas_heater_esp32_cam_snapshot.jpg"
                caption: "[View Live Feed](https://my-hass-base-url/api/camera_proxy/camera.gas_heater_cam_gas_heater_esp32_cam?token={{ state_attr('camera.gas_heater_cam_gas_heater_esp32_cam', 'access_token') }})"
                parse_mode: markdown
```

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
