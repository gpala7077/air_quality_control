# Installation
Assumption: You have already installed **HACS**, **AppDaemon**, **MariaDB** and  **Gerardo's ReGex SmartHome Entity Matching** App.
1. If you do not have HACS installed, please follow the instructions here: https://hacs.xyz/docs/installation/manual.
2. If you do not have AppDaemon installed, please follow the instructions here:https://appdaemon.readthedocs.io/en/latest/INSTALL.html
3. If you do not have MariaDB installed, please follow the instructions here: https://github.com/home-assistant/addons/blob/master/mariadb/DOCS.md
4. If you do not have Gerardo's ReGex SmartHome Entity Matching App installed, please follow the instructions here: https://github.com/gpala7077/regex_smart_home


This repository is not part of the default HACS store. To add it to your HACS, you need to add it as a
custom repository. To do this, go to the HACS settings and add the following URL as a custom repository and choose
'AppDaemon' as the category:

Enter this URL: https://github.com/gpala7077/air_quality_control.git

It will look like this:
  <div style="display: flex; justify-content: space-around;">
  <div><img src="/static/custom_repository.png" alt="Custom Repo" style="width: 50%; max-width: 500px;"/></div>
  </div>



# Configuration
This is an example configuration file with all the available settings. 
Add the following to your `air_quality.yaml` file.

```yaml
automations:
  module: utility
  class: true

air_quality:
  module: air_quality
  class: AirQuality
  plugin:
    - HASS
  priority: 2
  use_dictionary_unpacking: True


  dependencies:
    - automations

  timezone: America/Chicago
  priority_time: 600 # 600 is the default value (seconds)
  inactivity_time: 600 # 600 is the default value (seconds)
  occupied_rooms_only: True # True is the default value
  sensor_deviation: .30 # 0.30 is the default value

  cron_job_schedule:
    air_circulation:
        interval: 7200 # 3600 is the default value (seconds)
        function: run_every
        time_pattern: 00:00:00
        run_immediately: False
        minutes: 10

    humidify:
        interval: 3600 # 3600 is the default value (seconds)
        function: run_every
        time_pattern: 00:15:00
        run_immediately: False
        minutes: 10

    deodorize_and_refresh:
        interval: 3600 # 3600 is the default value (seconds)
        function: run_every
        time_pattern: 00:30:00
        run_immediately: False
        minutes: 10

  use_regex_matching: True # True is the default value
  regex_matching:
    devices:
      humidifier: humidifier$
      purifier: purifier$
      oil_diffuser: oil_diffuser$

    sensors:
      humidity: .*_current_humidity
      pm2_5: .*_pm2_5
      occupancy: occupancy

  # If you do not want auto-matching, then specify the devices and sensors
  rooms:
    living_room:
      devices:
        purifier:
          - fan.office_purifier
        humidifier:
          - humidifier.living_room_humidifier

        oil_diffuser:
          - humidifier.office_oil_diffuser
      sensors:
        humidity:
          - sensor.office_humidifier_current_humidity
          - sensor.office_oil_diffuser_current_humidity
        pm2_5:
          - sensor.office_purifier_pm2_5
        occupancy:
          - binary_sensor.office_occupancy_general_1
          - binary_sensor.office_occupancy_snack

  # Enter entity id and the value that corresponds to 'sleep' or 'work' mode
  modes:
    sleep:
      - entity_id: input_text.iphone_eva_focus
        device_types:
          - humidifier
          - purifier
          - oil_diffuser

        value:
          - Sleep

    work:
      - entity_id: input_text.iphone_eva_focus
        device_types:
          - humidifier
          - purifier
          - oil_diffuser

        value:
          - Work
          - Commute

      - entity_id: input_text.iphone_gerardo_focus
        device_types:
          - humidifier
          - purifier
          - oil_diffuser

        value:
          - Work
          - Commute

  logging:
    room: office
    level: INFO
    function: all
```


The most basic configuration to start out with can be as simple as if you are using ReGex Matching.

This will auto-discover your entities and rooms accordingly.
It assumes the following naming convention:
domain.room_device_type
or 
domain_room_device_type_sensor

so for example:
- humidifier.living_room_humidifier
- sensor.living_room_humidifier_current_humidity

or
- binary_sensor.living_room_occupancy_1
- binary_sensor.living_room_occupancy_2

or 
- fan.living_room_purifier
- sensor.living_room_purifier_pm2_5

I provided the default values for ReGex Matching but you can tweak them to your liking.

```yaml
air_quality:
  module: air_quality
  class: AirQuality
  plugin:
    - HASS
  priority: 2
  use_dictionary_unpacking: True
  
  # REQUIRED:
  timezone: America/Chicago # Your timezone

  use_regex_matching: True # True is the default value
  regex_matching:
    devices:
      humidifier: humidifier$
      purifier: purifier$
      oil_diffuser: oil_diffuser$

    sensors:
      humidity: .*_current_humidity
      pm2_5: .*_pm2_5
      occupancy: occupancy

```
or if you are not using ReGex Matching, then you can specify the devices and sensors for each room.
```yaml
air_quality:
  module: air_quality
  class: AirQuality
  plugin:
    - HASS
  priority: 2
  use_dictionary_unpacking: False
  
  # REQUIRED:
  timezone: America/Chicago # Your timezone

  rooms:
    living_room:
      devices:
        purifier:
          - fan.office_purifier
        humidifier:
          - humidifier.living_room_humidifier

        oil_diffuser:
          - humidifier.office_oil_diffuser
      sensors:
        humidity:
          - sensor.office_humidifier_current_humidity
          - sensor.office_oil_diffuser_current_humidity
        pm2_5:
          - sensor.office_purifier_pm2_5
        occupancy:
          - binary_sensor.office_occupancy_general_1
          - binary_sensor.office_occupancy_snack
```


# Air Quality Automation Documentation

---

## What the Automation Does

The Air Quality Automation system intelligently manages indoor air quality using air purifiers, humidifiers, and
diffusers. It's designed to automatically adjust these devices based on real-time air quality data, ensuring a healthy
and comfortable environment.

There are two main components to the Air Quality Automation system, first responds to room activity and environmental
changes, and the second is a set of cron jobs that run on a schedule. The main automations are triggered when there is
activity in the room and self-adjusts as the environment changes. The cron jobs are designed to run at specific
times of the day to perform tasks such as circulating air, refreshing and deodorizing, and humidifying.

### Room Activity Automation - Real-time Automation

- Monitors air quality through a combination of sensors, including humidity and particulate matter
- Utilizes a priority algorithm to assess and respond to air quality changes.
- Adjusts air treatment devices as needed, based on specific air quality metrics.
  - If humidity is too low, the humidifier will be turned on.
  - If particulate matter is too high, the air purifier will be turned on.
  - If the air quality and humidity is good, the diffuser will be turned on.
  - If any devices conflict, the priority algorithm will determine which device to turn on.

### Cron Jobs - Scheduled Automation

- Circulating Air
  - Turns on all purifiers and fans for 10 minutes every hour

- Humidify
  - Turns on the humidifier for 10 minutes every hour at the 15th minute

- Refresh and Deodorize
  - Turns on the diffusers for 10 minutes every hour at the 30th minute

---

## Deep Dive into the Air Quality Automation System

### System Overview

The Air Quality Automation system employs a multi-faceted approach to maintain and optimize indoor air quality. It
integrates with various air treatment devices and analyzes sensor data and control device settings.

### Main Components

#### Data Collection and Analysis

The system continuously monitors environmental parameters using sensors in the current room. It also collects data from
the air treatment devices, including the current state and settings. This data is used to determine the current air
quality and the optimal settings for the air treatment devices. The system prioritizes the air treatment devices based
on the ratio between the current and optimal values and scored using an importance algorithm. The device with the
highest importance score will be turned on.

##### Example:

Imagine a room with the following environmental conditions:

- **Humidity**: 40% (indicating the air is quite dry)
- **Particulate Matter**: 100 (showing a higher level of dust)
- **Diffuser**: Currently off

In this scenario, the air is not only dry but also contains a significant amount of dust. Operating both the humidifier
and the air purifier simultaneously could lead to conflicts in their functions. For instance, while the air purifier is
working to clean the air, it might inadvertently collect excessive moisture if the humidifier is on, potentially
damaging its filter.

So, which device should be activated under these conditions? Ideally, we aim for:

1. **Humidity**: To be maintained within a comfortable range of 40% to 60%.
2. **Particulate Matter**: To be reduced to a level below 50 for cleaner air.

Given these targets, the system's scoring algorithm evaluates which device to prioritize. In this case, it would select
the humidifier for activation first, addressing the immediate concern of low humidity. The humidifier would operate
until the room's humidity reaches the upper end of the ideal range (60%), or until the dust level becomes the more
pressing issue, necessitating a switch to the air purifier.

Once the humidity and particulate matter levels are optimized, and with both within their ideal ranges, the system can
then proceed to activate the diffuser. This sequence ensures that the room's air quality is managed efficiently without
device conflicts, maintaining both comfort and device integrity.

#### Scoring Algorithm

The scoring algorithm looks at the **ratio between the current value and the optimal value** to determine the score. The
score is then used to determine the priority of the device. The device with the highest priority will be turned on.
For more detailed information on the scoring algorithm, see the
[scoring algorithm documentation](https://github.com/gpala7077/regex_smart_home/tree/master?tab=readme-ov-file#scoring-algorithm)

### Master Air Quality Logic

The main function serves as the brain of the Air Quality Automation system. Its primary role is to orchestrate the
behavior of various devices that influence air quality, such as air purifiers, humidifiers, and oil diffusers. This
process is based on a comprehensive analysis of air quality metrics, user preferences, and environmental conditions in a
specific room.

#### Core Functionality

- **Dynamic Response to Air Quality**: The function continuously monitors the air quality data and dynamically adjusts
  the operation of the devices to maintain optimal air conditions.
- **Intelligent Decision-Making**: It employs an algorithm to prioritize which device should be active at
  any given time, ensuring efficiency and effectiveness in air quality management.
- **User Preferences and Automation Settings**: The logic takes into account user-defined settings, allowing for a
  tailored experience. Whether it's based on automated schedules or manual overrides, the function respects these
  preferences while making decisions.
- **Holistic Room Analysis**: It doesn't just focus on a single device or sensor. Instead, the function considers the
  collective status of all devices and sensors in a room, ensuring a holistic approach to managing air quality.

#### Impact and Benefits

- **Enhanced Indoor Comfort**: By accurately adjusting air quality devices, the function ensures a comfortable indoor
  environment that is responsive to both the needs of the occupants and the changing environmental conditions.
- **Energy Efficiency**: Smart management of devices leads to optimized energy usage, as devices are only active when
  necessary and operate at appropriate levels.
- **User Convenience**: The automation minimizes the need for manual intervention, providing a convenient and worry-free
  experience for the users.

---