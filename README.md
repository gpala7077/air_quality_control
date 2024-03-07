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
  <div><img src="/apps/static/custom_repository.png" alt="Custom Repo" style="width: 50%; max-width: 500px;"/></div>
  </div>



# Configuration
This is an example configuration file with all the available settings. 
Add the following to your `air_quality.yaml` file.

```yaml
air_quality:
  module: air_quality
  class: AirQuality
  plugin:
    - HASS
  priority: 2
  use_dictionary_unpacking: True


  dependencies:
    - automations

  # Air Quality Automation
  # OPTIONAL: This can be commented out or removed entirely
  priority_time: 600 # 600 is the default value (seconds)
  inactivity_time: 600 # 600 is the default value (seconds)
  occupied_rooms_only: True # True is the default value
  sensor_deviation: .30 # 0.30 is the default value

  # Cron Jobs Schedule
  cron_job_schedule:
    air_circulation:
      interval: 7200 # 7200 is the default value (seconds)
      hour: 0
      minute: 0
      second: 0
    humidify:
      interval: 3600 # 3600 is the default value (seconds)
      hour: 0
      minute: 15
      second: 0
    deodorize_and_refresh:
      interval: 3600 # 3600 is the default value (seconds)
      hour: 0
      minute: 30
      second: 0
  
  # Auto match your entities and rooms
  use_regex_matching: True # True is the default value
  regex_matching:
    devices:
      humidifier: humidifier$
      purifier: purifier$
      oil_diffuser: oil_diffuser$

    sensors:
      current_humidity: .*_current_humidity
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
        current_humidity:
          - sensor.office_humidifier_current_humidity
          - sensor.office_oil_diffuser_current_humidity
        pm2_5:
          - sensor.office_purifier_pm2_5
        occupancy:
          - binary_sensor.office_occupancy_general_1
          - binary_sensor.office_occupancy_snack
  
  # Enter entity id and the value that corresponds to 'sleep' or 'work' mode
  # OPTIONAL: This can be commented out or removed entirely
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
```


The most basic configuration to start out with can be as simple as if you are using ReGex Matching.
```yaml
air_quality:
  module: air_quality
  class: AirQuality
  plugin:
    - HASS
  priority: 2
  use_dictionary_unpacking: True

  use_regex_matching: True # True is the default value
  regex_matching:
    devices:
      humidifier: humidifier$
      purifier: purifier$
      oil_diffuser: oil_diffuser$

    sensors:
      current_humidity: .*_current_humidity
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
        current_humidity:
          - sensor.office_humidifier_current_humidity
          - sensor.office_oil_diffuser_current_humidity
        pm2_5:
          - sensor.office_purifier_pm2_5
        occupancy:
          - binary_sensor.office_occupancy_general_1
          - binary_sensor.office_occupancy_snack
```