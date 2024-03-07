import appdaemon.plugins.hass.hassapi as hass
from datetime import datetime, timedelta, time
import numpy as np


class AirQuality(hass.Hass):
    """AirQuality class."""

    def initialize(self):
        """Initialize the HACS app."""
        self.log("Air Quality Priority System is initializing")
        self.automations = self.get_app('automations')
        self.turn_off_logic = {
            'purifier': self.turn_off_purifier,
            'humidifier': self.turn_off_humidifier,
            'oil_diffuser': self.turn_off_diffuser,
        }
        self.turn_on_logic = {
            'purifier': self.turn_on_purifier,
            'humidifier': self.turn_on_humidifier,
            'oil_diffuser': self.turn_on_diffuser,
        }
        self.continue_logic = {
            'purifier': self.set_purifier_mode,
            'humidifier': self.set_humidifier_mode,
            'oil_diffuser': self.set_diffuser_mode
        }
        self.room_sensor_data = {}
        self.diffuser_cycle_thread = {}
        self.master_air_quality_thread = {}
        self.room_penalties_data = {}
        self.debounce_timers = {}
        self.priority_devices = {}
        self.cron_jobs = {}
        self.debounce_period = timedelta(seconds=60)  # 60 seconds
        self.create_automation_entities()
        self.create_room_based_automations()
        self.create_cron_jobs()
        self.log("Air Quality Priority System is initialized")

    def create_cron_jobs(self):
        """Create cron jobs."""

        cron_jobs = {
            'Air Circulation': dict(
                run_on_reload=False,  # Don't run the automation immediately
                minutes=10,  # Amount of time to run the automation. Specific to circulate_air_logic
                cron_pattern=time(
                    self.args.get('cron_job_schedule', {}).get('air_circulation', {}).get('hour', 0),
                    self.args.get('cron_job_schedule', {}).get('air_circulation', {}).get('minute', 0),
                    self.args.get('cron_job_schedule', {}).get('air_circulation', {}).get('second', 0)
                ),  # Every 2 hours on the hour
                cron_func='run_every',
                cron_interval=self.args.get('cron_job_schedule').get('air_circulation').get('interval', 60*60*2),
                logic_func=self.circulate_air_logic,
            ),

            'Humidify': dict(
                run_on_reload=False,  # Don't run the automation immediately
                minutes=5,  # Amount of time to run the automation. Specific to humidifier_logic
                cron_pattern=time(
                    self.args.get('cron_job_schedule', {}).get('humidify', {}).get('hour', 0),
                    self.args.get('cron_job_schedule', {}).get('humidify', {}).get('minute', 15),
                    self.args.get('cron_job_schedule', {}).get('humidify', {}).get('second', 0)
                ),  # Every 2 hours on the hour
                cron_func='run_every',
                cron_interval=self.args.get('cron_job_schedule', {}).get('humidify', {}).get('interval', 60*60),
                logic_func=self.humidify_logic,
            ),

            'Deodorize and Refresh': dict(
                run_on_reload=False,  # Don't run the automation immediately
                minutes=2,  # Amount of time to run the automation. Specific to deodorize_and_refresh_logic
                cron_pattern=time(
                    self.args.get('cron_job_schedule', {}).get('deodorize_and_refresh', {}).get('hour', 0),
                    self.args.get('cron_job_schedule', {}).get('deodorize_and_refresh', {}).get('minute', 30),
                    self.args.get('cron_job_schedule', {}).get('deodorize_and_refresh', {}).get('second', 0)
                ),  # Every 2 hours on the hour
                cron_func='run_every',
                cron_interval=self.args.get('cron_job_schedule').get('deodorize_and_refresh').get('interval', 60*60),
                logic_func=self.deodorize_and_refresh_logic,
            )
        }

        for job, config in cron_jobs.items():
            cron_pattern = config.pop('cron_pattern')
            cron_pattern = datetime.combine(datetime.now().date(), cron_pattern)
            run_on_reload = config.pop('run_on_reload')
            cron_func = config.pop('cron_func')
            cron_window = config.pop('cron_interval', None)
            minutes = config.pop('minutes', 0)

            if run_on_reload:
                config['logic_func']()

            if cron_func == 'run_hourly':
                self.run_hourly(config['logic_func'], start=cron_pattern, minutes=minutes)

            elif cron_func == 'run_every':
                self.run_every(config['logic_func'], start=cron_pattern, interval=cron_window, minutes=minutes)

    def create_automation_entities(self):
        """Create the automation entities."""
        device_types = ['purifier', 'oil_diffuser', 'humidifier']

        # Create the master automation switches
        for device_type in device_types:
            # Check if entity already exists and if so, don't override user settings
            if self.get_state(f'input_boolean.automatic_{device_type}') is None:
                self.set_state(
                    f'input_boolean.automatic_{device_type}',
                    state='on',
                    attributes={"friendly_name": "Automatic " + device_type.replace('_', ' ').title()}
                )

        # Create Cron Job Switches
        cron_jobs = [
            'automatic_air_circulation',
            'automatic_deodorize_and_refresh',
            'automatic_humidify',
        ]

        for cron_job in cron_jobs:
            # Check if entity already exists and if so, don't override user settings
            if self.get_state(f'input_boolean.{cron_job}') is None:
                self.set_state(
                    f'input_boolean.{cron_job}',
                    state='on',
                    attributes={"friendly_name": cron_job.replace('_', ' ').title()}
                )

        # Create room-level automation switches
        room_config = self.automations.areas if self.args.get('use_regex_matching', True) else self.args.get('rooms')
        for room_id, room_name in room_config.items():
            self.master_air_quality_thread[room_id] = {}
            self.room_penalties_data[room_id] = {}
            self.room_sensor_data[room_id] = {}
            self.diffuser_cycle_thread[room_id] = {}
            self.priority_devices[room_id] = {'device': 'purifier', 'time': datetime.now() - timedelta(seconds=600)}
            self.diffuser_cycle_thread[room_id] = True
            self.cron_jobs[room_id] = {}
            self.get_sensor_data(room_id)  # Initialize sensor data
            self.set_state(f'input_text.{room_id}_air_quality_priority_device', state='purifier')
            for device_type in device_types:
                if self.get_state(f'input_boolean.{room_id}_{device_type}_auto') is None:
                    self.set_state(
                        f'input_boolean.{room_id}_{device_type}_auto',
                        state='on',
                        attributes={"friendly_name": f"{room_name} {device_type.replace('_', ' ').title()} Auto"}
                    )
                if device_type == 'oil_diffuser':

                    # Create Oil Diffuser Settings: Min 1; Max 10; Step 1
                    if self.get_state(f'input_number.{room_id}_oil_grade_level') is None:
                        self.set_state(
                            f'input_number.{room_id}_oil_grade_level',
                            state=4,
                            attributes={"friendly_name": f"{room_name} Oil Grade Level"},
                            min=1,
                            max=10,
                            step=1
                        )
                elif device_type == 'humidifier':
                    # Create Humidifier Settings: Min 1; Max 100; Step 1
                    if self.get_state(f'input_number.{room_id}_humidity_tolerance') is None:
                        self.set_state(
                            f'input_number.{room_id}_humidity_tolerance',
                            state=60,
                            attributes={"friendly_name": f"{room_name} Humidity Tolerance"},
                            min=35,
                            max=100,
                            step=1
                        )
                    if self.get_state(f'input_number.{room_id}_humidity_target') is None:
                        self.set_state(
                            f'input_number.{room_id}_humidity_target',
                            state=60,
                            attributes={"friendly_name": f"{room_name} Humidity Target"},
                            min=35,
                            max=100,
                            step=1
                        )
                elif device_type == 'purifier':
                    # Create Purifier Settings:
                    thresholds = {
                        "pm2_5_low": (10, 25),
                        "pm2_5_medium_low": (50, 50),
                        "pm10_medium_high": (70, 75),
                        "pm10_high": (100, 100)
                    }
                    for threshold, value in thresholds.items():
                        if self.get_state(f'input_number.{room_id}_thresholds_{threshold}') is None:
                            self.set_state(
                                f'input_number.{room_id}_thresholds_{threshold}',
                                state=value[0],
                                attributes={
                                    "friendly_name": f"{room_name} {threshold.replace('_', ' ').title()} Threshold"},
                                min=0,
                                max=500,
                                step=10
                            )
                        if self.get_state(f'input_number.{room_id}_percentage_{threshold}') is None:
                            self.set_state(
                                f'input_number.{room_id}_percentage_{threshold}',
                                state=value[1],
                                attributes={
                                    "friendly_name": f"{room_name} Percentage {threshold.replace('_', ' ').title()}"},
                                min=0,
                                max=100,
                                step=1
                            )

    def get_air_quality_entities(self, room):
        """Get air quality entities for the specified room."""
        if self.args.get('use_regex_matching', True):
            return {  # Get Device Status
                'purifier': self.automations.get_matching_entities(
                    area=room,
                    domain='fan',
                    pattern=self.args.get('regex_matching').get('devices').get('purifier', 'purifier$')
                ),
                'humidifier': self.automations.get_matching_entities(
                    area=room,
                    domain='humidifier',
                    pattern=self.args.get('regex_matching').get('devices').get('humidifier', 'humidifier$')
                ),
                'oil_diffuser': self.automations.get_matching_entities(
                    area=room,
                    domain='humidifier',
                    pattern=self.args.get('regex_matching').get('devices').get('oil_diffuser', 'oil_diffuser$')
                ),
            }
        else:
            config = self.args.get('rooms').get(room).get('devices')
            purifiers = {entity: self.get_state(entity) for entity in config.get('purifier', [])}
            humidifiers = {entity: self.get_state(entity) for entity in config.get('humidifier', [])}
            diffusers = {entity: self.get_state(entity) for entity in config.get('oil_diffuser', [])}

            return {
                'purifier': purifiers,
                'humidifier': humidifiers,
                'oil_diffuser': diffusers,
            }

    def get_user_overrides(self, room):

        return {  # Get Device Status
            'purifier': self.automations.get_matching_entities(
                    area=room,
                    domain='input_boolean',
                    pattern=f'purifier_auto',
                    agg_func='count',
                    index='state'
                ).get('off', 0) == 1
            ,
            'humidifier': self.automations.get_matching_entities(
                    area=room,
                    domain='input_boolean',
                    pattern=f'humidifier_auto',
                    agg_func='count',
                    index='state'
                ).get('off', 0) == 1
            ,
            'oil_diffuser': self.automations.get_matching_entities(
                    area=room,
                    domain='input_boolean',
                    pattern=f'oil_diffuser_auto',
                    agg_func='count',
                    index='state'
                ).get('off', 0) == 1
        }

    def get_master_overrides(self):
        return {
            'purifier': self.get_state('input_boolean.automatic_purifier') == 'off',
            'humidifier': self.get_state('input_boolean.automatic_humidifier') == 'off',
            'oil_diffuser': self.get_state('input_boolean.automatic_oil_diffuser') == 'off',
        }

    def is_room_occupied(self, room):
        """Get the room occupancy."""
        if self.args.get('use_regex_matching', True):
            occupancy = self.automations.get_matching_entities(
                domain='binary_sensor',
                area=room,
                pattern=self.args.get('regex_matching').get('sensors').get('occupancy', 'occupancy'),
                agg_func='count',
                index='state'
            )

        else:
            config = self.args.get('rooms').get(room)
            occupancy = {}
            for entity in config.get('occupancy', []):
                if self.get_state(entity) in occupancy:
                    occupancy[self.get_state(entity)] += 1
                else:
                    occupancy.update({self.get_state(entity): 1})

        return occupancy.get('on', 0) > 0

    def get_sensor_data(self, room):

        if self.args.get('use_regex_matching', True):
            pm2_5 = self.automations.get_matching_entities(
                area=room,
                domain='sensor',
                pattern=self.args.get('regex_matching').get('sensors').get('pm2_5', '.*_pm2_5'),
                agg_func='mean'
            )

            current_humidity = self.automations.get_matching_entities(
                area=room,
                domain='sensor',
                pattern=self.args.get('regex_matching').get('sensors').get('current_humidity', '.*_current_humidity'),
                agg_func='mean'
            )

            self.room_sensor_data[room] = {
                'recorded': datetime.now(),
                'pm2_5': pm2_5 if pm2_5 else 0,
                'current_humidity': current_humidity if current_humidity else 45
            }
        else:
            config = self.args.get('rooms').get(room).get('sensors')
            pm2_5 = {entity: self.get_state(entity) for entity in config.get('pm2_5', [])}
            humidity = {entity: self.get_state(entity) for entity in config.get('current_humidity', [])}

            self.room_sensor_data[room] = {
                'recorded': datetime.now(),
                'pm2_5': np.mean([float(value) for value in pm2_5.values()] or 0),
                'current_humidity': np.mean([float(value) for value in humidity.values()] or 45)
            }
        return self.room_sensor_data[room]

    def create_room_based_automations(self):
        """Create room based occupancy and sensor triggers."""
        # Get room configuration
        room_config = self.automations.areas if self.args.get('use_regex_matching', True) else self.args.get('rooms')

        for room_id, config in room_config.items():
            if self.args.get('use_regex_matching', True):
                binary_sensors = self.automations.get_matching_entities(
                    domain='binary_sensor',
                    area=room_id,
                    pattern=self.args.get('regex_matching').get('devices').get('occupancy', 'occupancy'),
                )

                pm2_5 = self.automations.get_matching_entities(
                    area=room_id,
                    domain='sensor',
                    pattern=self.args.get('regex_matching').get('devices').get('pm2_5', '.*_pm2_5'),
                    # agg_func='mean'
                )

                current_humidity = self.automations.get_matching_entities(
                    area=room_id,
                    domain='sensor',
                    pattern=self.args.get('regex_matching').get('devices').get('current_humidity','.*_current_humidity'),
                    # agg_func='mean'
                )

            else:
                config = config.get('sensors')
                binary_sensors = config.get('occupancy', [])
                pm2_5 = config.get('pm2_5', [])
                current_humidity = config.get('current_humidity', [])

            # Get all device statuses
            controllable = self.get_air_quality_entities(room_id)

            # Listen for occupancy changes
            for binary_sensor in binary_sensors:
                if any([bool(device) for device in controllable.values()]):
                    self.listen_state(
                        self.master_air_quality_logic,
                        binary_sensor,
                        new='on',
                        room=room_id,
                    )
                    self.listen_state(
                        self.turn_off_air_quality_devices,
                        binary_sensor,
                        new='off',
                        room=room_id,
                        include_priority=True,
                        duration=self.args.get('inactivity_time', 600),
                        check_for_occupancy=True,
                    )

            # Listen for sensor changes
            for sensor in pm2_5:
                self.listen_state(
                    self.check_sensor_changes,
                    sensor,
                    room=room_id,
                    sensor_type='pm2_5'
                )
            for sensor in current_humidity:
                self.listen_state(
                    self.check_sensor_changes,
                    sensor,
                    room=room_id,
                    sensor_type='current_humidity'
                )

    def create_room_based_automations_hardcoded(self):
        """Create room based occupancy and sensor triggers."""
        # Get room configuration
        room_config = self.args.get('rooms')
        for room_id, config in room_config.items():
            binary_sensors = config.get('occupancy', [])
            pm2_5 = config.get('pm2_5', [])
            current_humidity = config.get('current_humidity', [])

            # Get all device statuses
            controllable = self.get_air_quality_entities(room_id)

            # Listen for occupancy changes
            for binary_sensor in binary_sensors:
                if any([bool(device) for device in controllable.values()]):
                    self.listen_state(
                        self.master_air_quality_logic,
                        binary_sensor,
                        new='on',
                        room=room_id,
                    )
                    self.listen_state(
                        self.turn_off_air_quality_devices,
                        binary_sensor,
                        new='off',
                        room=room_id,
                        include_priority=True,
                        duration=self.args.get('inactivity_time', 600),
                        check_for_occupancy=True,
                    )

            # Listen for sensor changes
            for sensor in pm2_5:
                self.listen_state(
                    self.check_sensor_changes,
                    sensor,
                    room=room_id,
                    sensor_type='pm2_5'
                )
            for sensor in current_humidity:
                self.listen_state(
                    self.check_sensor_changes,
                    sensor,
                    room=room_id,
                    sensor_type='current_humidity'
                )

    def check_sensor_changes(self, *args, **kwargs):
        room = kwargs.get('room')
        sensor_type = kwargs.get('sensor_type')
        debounce_key = f'{room}_{sensor_type}_sensor_changes'
        new = float(args[3])
        if self.should_debounce(debounce_key):
            return

        # If room is not occupied and occupancy is required, don't run the logic
        if not self.is_room_occupied(room) and self.args.get('occupied_rooms_only', True):
            return

        last_reading = self.room_sensor_data[room].get(sensor_type)

        if abs((new / last_reading) - 1) > self.args.get('sensor_deviation', .30):
            self.log(
                f"""
                In check_sensor_changes - {room}:
                {sensor_type} has changed by more than 30%.
                Last Reading: {last_reading}
                Current Reading: {new}
                """,
                level='INFO'
            )
            self.get_sensor_data(room)  # Update sensor data
            self.run_in(self.master_air_quality_logic, 0, room=room)

    def turn_off_air_quality_devices(self, *args, **kwargs):
        room = kwargs.get('room')
        check_for_occupancy = kwargs.get('check_for_occupancy', False)
        include_priority = kwargs.get('include_priority', False)
        priority_device = self.priority_devices.get(room)['device']

        debounce_key = f'{room}_turn_off_air_quality_devices'

        if not self.execute_turn_off_command(room, debounce_key, check_for_occupancy):
            return

        # Turn off devices
        for other_device, other_func in self.turn_off_logic.items():
            if include_priority:
                self.turn_off_logic[other_device](room=room)

            elif not include_priority and other_device != priority_device:
                self.turn_off_logic[other_device](room=room)

    def turn_off_diffuser(self, room, **kwargs):
        if self.args.get('use_regex_matching', True):
            self.automations.command_matching_entities(
                hacs_commands='turn_off',
                area=room,
                domain=['humidifier'],
                pattern=self.args.get('regex_matching').get('devices').get('oil_diffuser', 'oil_diffuser$'),
            )

            self.automations.command_matching_entities(
                hacs_commands='turn_off',
                area=room,
                domain=['light'],
                pattern=self.args.get('regex_matching').get('devices').get('oil_diffuser', 'oil_diffuser$').strip('$'),
            )

        else:
            oil_diffuser = self.get_air_quality_entities(room).get('oil_diffuser')
            self.automations.command_matching_entities(
                hacs_commands='turn_off',
                area=room,
                domain=['humidifier'],
                include_only=True,
                include_manual_entities=list(oil_diffuser.keys()),
            )

    def turn_off_humidifier(self, room, **kwargs):
        if self.args.get('use_regex_matching', True):
            self.automations.command_matching_entities(
                hacs_commands='turn_off',
                area=room,
                domain='humidifier',
                pattern=self.args.get('regex_matching').get('devices').get('humidifier', 'humidifier$'),
            )
        else:
            humidifier = self.get_air_quality_entities(room).get('humidifier')
            self.automations.command_matching_entities(
                hacs_commands='turn_off',
                area=room,
                domain=['humidifier'],
                include_only=True,
                include_manual_entities=list(humidifier.keys()),
            )

    def turn_off_purifier(self, room, **kwargs):

        if self.args.get('use_regex_matching', True):
            self.automations.command_matching_entities(
                hacs_commands='turn_off',
                area=room,
                domain='fan',
                pattern=self.args.get('regex_matching').get('devices').get('purifier', 'purifier$'),
            )
        else:
            purifier = self.get_air_quality_entities(room).get('purifier')
            self.automations.command_matching_entities(
                hacs_commands='turn_off',
                area=room,
                domain=['fan'],
                include_only=True,
                include_manual_entities=list(purifier.keys()),
            )

    def execute_turn_off_command(self, room, debounce_key, check_for_occupancy=False):

        if self.should_debounce(debounce_key):
            return False

        if room is None:
            self.log(f"Room is not defined. Exiting...", level='INFO')
            return False

        if self.is_room_occupied(room) and check_for_occupancy:
            self.log(f"{room.title()} is still in use. Exiting...", level='INFO')
            return False

        return True

    def turn_on_purifier(self, room, **kwargs):
        pm2_5 = self.room_sensor_data[room]['pm2_5']
        fan_percentage = self.get_fan_percentage(pm2_5)  # Get fan percentage based on pm2.5 value
        if self.args.get('use_regex_matching', True):
            response = self.automations.command_matching_entities(
                hacs_commands={
                    'turn_on': {},
                    'set_percentage': {'percentage': fan_percentage}
                },
                area=room,
                domain='fan',
                pattern=self.args.get('regex_matching').get('devices').get('purifier', 'purifier$'),
                device_state=['off', 'unavailable']
            )
        else:
            purifier = self.get_air_quality_entities(room).get('purifier')
            response = self.automations.command_matching_entities(
                hacs_commands={
                    'turn_on': {},
                    'set_percentage': {'percentage': fan_percentage}
                },
                area=room,
                domain='fan',
                include_only=True,
                include_manual_entities=list(purifier.keys()),
                device_state=['off', 'unavailable']
            )

        if response:
            # Set fan percentage
            self.log(
                msg=f"""
                    In air_quality_logic - {room}:
                    Setting fan percentage to {fan_percentage}%
                    """,
                level='INFO',
            )

    def turn_on_humidifier(self, room, **kwargs):
        humidity_tolerance = float(self.get_state(f"input_number.{room}_humidity_tolerance"))
        humidity_target = float(self.get_state(f"input_number.{room}_humidity_tolerance"))
        current_humidity = self.room_sensor_data[room]['current_humidity']

        if current_humidity <= humidity_tolerance:
            if self.args.get('use_regex_matching', True):
                response = self.automations.command_matching_entities(
                    hacs_commands={
                        'turn_on': {},
                        'set_mode': {'mode': 'manual'},
                        'set_humidity': {'humidity': humidity_target}
                    },
                    area=room,
                    domain='humidifier',
                    pattern=self.args.get('regex_matching').get('devices').get('humidifier', 'humidifier$'),
                    device_state=['off', 'unavailable']
                )
            else:
                humidifier = self.get_air_quality_entities(room).get('humidifier')
                response = self.automations.command_matching_entities(
                    hacs_commands={
                        'turn_on': {},
                        'set_mode': {'mode': 'manual'},
                        'set_humidity': {'humidity': humidity_target}
                    },
                    area=room,
                    domain='humidifier',
                    include_only=True,
                    include_manual_entities=list(humidifier.keys()),
                    device_state=['off', 'unavailable']
                )
            if response:
                self.log(
                    f"""
                        In humidifier_logic - {room}:
                        Turning on humidifier.
                        {response}
                    """,
                    level='INFO',
                )

            else:
                self.log(
                    f"""
                        In humidifier_logic - {room}:
                        Humidifier is already on.
                    """,
                    level='INFO',
                )

    def turn_on_diffuser(self, room, **kwargs):
        self.run_in(self.diffuser_cycle_logic, 0, room=room)

    def master_air_quality_logic(self, *args, **kwargs):

        room = kwargs.get('room')
        debounce_key = f'{room}_air_quality_logic'
        if self.should_debounce(debounce_key):
            return

        # All these conditions must be True for automatic air quality device to run
        conditions = {
            'master_automations_off': all([not is_running for job, is_running in self.cron_jobs[room].items()]),
        }

        # If all conditions are True, run the automation
        if all(conditions.values()):
            user_overrides = self.get_user_overrides(room)
            master_overrides = self.get_master_overrides()
            priority_device = self.decide_device_activation(room)

            if user_overrides[priority_device] or master_overrides[priority_device]:
                self.log(
                    f"""
                        In master_air_quality_logic - {room}:
                        {priority_device.title()} is disabled by user. Skipping Logic...
                        
                        Disabled by User: {user_overrides}
                        Disabled by Master: {master_overrides}
                    """,
                    level='INFO',
                )
                return

            # Check mode and set device accordingly
            continue_with_automation = self.continue_logic[priority_device](room)

            if continue_with_automation:  # If mode behavior was triggered. Don't continue air quality logic
                # Turn on the device
                self.run_in(
                    self.turn_on_logic[priority_device],
                    delay=0,
                    room=room,
                )

            # Turn off other devices
            self.run_in(
                self.turn_off_air_quality_devices,
                delay=0,
                room=room,
                include_priority=False
            )

    def humidify_logic(self, *args, **kwargs):
        debounce_key = f'air_quality_humidify'
        if self.should_debounce(debounce_key):
            return
        rooms = self.automations.areas if self.args.get('use_regex_matching', True) else self.args.get('rooms')

        for area in rooms:
            self.priority_devices[area] = {'device': 'humidifier', 'time': datetime.now()}
            humidity_tolerance = float(self.get_state(f"input_number.{area}_humidity_tolerance"))
            humidity_target = float(self.get_state(f"input_number.{area}_humidity_target"))

            if self.args.get('use_regex_matching', True):
                commands = [
                    dict(
                        hacs_commands={
                            'turn_on': {},
                            'set_mode': {'mode': 'manual'},
                            'set_humidity': {'humidity': humidity_target}
                        },
                        domain='humidifier',
                        pattern=self.args.get('regex_matching').get('devices').get('humidifier', 'humidifier$'),
                        area=area,
                    ),
                ]

                final_commands = [
                    dict(
                        hacs_commands='turn_off', 
                        domain='humidifier', 
                        pattern=self.args.get('regex_matching').get('devices').get('humidifier', 'humidifier$'),
                        area=area
                    )
                ]
            else:
                humidifier = self.get_air_quality_entities(area).get('humidifier')
                commands = [
                    dict(
                        hacs_commands={
                            'turn_on': {},
                            'set_mode': {'mode': 'manual'},
                            'set_humidity': {'humidity': humidity_target}
                        },
                        domain='humidifier',
                        include_only=True,
                        include_manual_entities=list(humidifier.keys()),
                        area=area
                    ),
                ]

                final_commands = [
                    dict(
                        hacs_commands='turn_off',
                        domain='humidifier',
                        include_only=True,
                        include_manual_entities=list(humidifier.keys()),
                        area=area
                    )
                ]
            # All boolean must be true in order to run Air Circulation Automation
            automation_boolean_checks = {
                'has_master_auto_on': self.get_state("input_boolean.automatic_humidify") == 'on',
            }
            self.turn_off_air_quality_devices(room=area, include_priority=False)
            self.automations.master_automation_logic(
                app_name='air_quality',
                task_id='humidify',
                master_name='humidify',
                boolean_checks=automation_boolean_checks,
                commands=commands,
                final_commands=final_commands,
                default_wait=15 * 60,
                **kwargs
            )

    def deodorize_and_refresh_logic(self, *args, **kwargs):
        debounce_key = f'air_quality_deodorize_and_refresh'
        if self.should_debounce(debounce_key):
            return

        current_time = datetime.now()
        rooms = self.automations.areas if self.args.get('use_regex_matching', True) else self.args.get('rooms')
        for area in rooms:
            self.priority_devices[area] = {'device': 'oil_diffuser', 'time': current_time}
            if self.args.get('use_regex_matching', True):
                pattern = self.args.get('regex_matching').get('devices').get('oil_diffuser', 'oil_diffuser$')
                commands = [
                    dict(
                        hacs_commands={
                            'turn_on': {},
                            'set_humidity': {'humidity': 100}
                        },
                        domain='humidifier',
                        pattern=pattern,
                        area=area,
                    ),
                    dict(
                        hacs_commands='turn_on',
                        domain='light',
                        pattern=pattern.strip('$'),
                        color_name='purple',
                        brightness=100,
                        area=area
                    )

                ]

                final_commands = [
                    dict(
                        hacs_commands='turn_off',
                        domain='humidifier',
                        pattern=self.args.get('regex_matching').get('devices').get('oil_diffuser', 'oil_diffuser$'),
                        area=area)
                ]

            else:
                oil_diffuser = self.get_air_quality_entities(area).get('oil_diffuser')
                commands = [
                    dict(
                        hacs_commands={
                            'turn_on': {},
                            'set_humidity': {'humidity': 100}
                        },
                        domain='humidifier',
                        include_only=True,
                        include_manual_entities=list(oil_diffuser.keys()),
                        area=area
                    ),
                ]

                final_commands = [
                    dict(
                        hacs_commands='turn_off',
                        domain='humidifier',
                        include_only=True,
                        include_manual_entities=list(oil_diffuser.keys()),
                        area=area
                    )
                ]
            # All boolean must be true in order to run Air Circulation Automation
            automation_boolean_checks = {
                'has_master_auto_on': self.get_state("input_boolean.automatic_deodorize_and_refresh") == 'on',
            }
            self.turn_off_air_quality_devices(room=area, include_priority=False)
            self.automations.master_automation_logic(
                app_name='air_quality',
                task_id='deodorize_and_refresh',
                master_name='deodorize_and_refresh',
                boolean_checks=automation_boolean_checks,
                commands=commands,
                final_commands=final_commands,
                default_wait=15 * 60,
                **kwargs
            )

    def circulate_air_logic(self, *args, **kwargs):
        debounce_key = f'air_quality_circulate_air'
        if self.should_debounce(debounce_key):
            return
        # Any boolean must be true to run Air Circulation quietly
        sleep_mode_boolean_checks = self.check_air_quality_mode_penalties('purifier')
        rooms = self.automations.areas if self.args.get('use_regex_matching', True) else self.args.get('rooms')
        for area in rooms:
            self.priority_devices[area] = {'device': 'purifier', 'time': datetime.now()}
            if self.args.get('use_regex_matching', True):
                commands = [
                    dict(
                        hacs_commands='turn_on',
                        domain='fan',
                        pattern=['.*_fan$', 'purifier$'],
                        area=area
                    ),
                    dict(
                        hacs_commands={
                            'set_percentage': dict(percentage=25),
                        } if any(sleep_mode_boolean_checks.values()) else {
                            'set_percentage': dict(percentage=100),
                            'set_preset_mode': dict(preset_mode='turbo')
                        },
                        domain='fan',
                        pattern=self.args.get('regex_matching').get('devices').get('purifier', 'purifier$'),
                        area=area
                    ),
                ]

                final_commands = [
                    dict(
                        hacs_commands='turn_off',
                        domain='fan',
                        pattern=self.args.get('regex_matching').get('devices').get('purifier', 'purifier$'),
                        area=area
                    )
                ]
            else:
                purifier = self.get_air_quality_entities(area).get('purifier')
                commands = [
                    dict(
                        hacs_commands='turn_on',
                        domain='fan',
                        include_only=True,
                        include_manual_entities=list(purifier.keys()),
                        area=area
                    ),
                    dict(
                        hacs_commands={
                            'set_percentage': dict(percentage=25),
                        } if any(sleep_mode_boolean_checks.values()) else {
                            'set_percentage': dict(percentage=100),
                            'set_preset_mode': dict(preset_mode='turbo')
                        },
                        domain='fan',
                        include_only=True,
                        include_manual_entities=list(purifier.keys()),
                        area=area
                    ),
                ]

                final_commands = [
                    dict(
                        hacs_commands='turn_off',
                        domain='fan',
                        include_only=True,
                        include_manual_entities=list(purifier.keys()),
                        area=area
                    )
                ]

            # All boolean must be true in order to run Air Circulation Automation
            automation_boolean_checks = {
                'has_master_auto_on': self.get_state("input_boolean.automatic_air_circulation") == 'on',
            }

            self.turn_off_air_quality_devices(room=area, include_priority=False)
            self.automations.master_automation_logic(
                app_name='air_quality',
                task_id='air_circulation',
                master_name='air_circulation',
                boolean_checks=automation_boolean_checks,
                commands=commands,
                final_commands=final_commands,
                default_wait=15 * 60,
                **kwargs
            )

    def decide_device_activation(self, room):
        # Get Room Status
        sensor_data = self.get_sensor_data(room)
        pm2_5 = sensor_data['pm2_5']
        current_humidity = sensor_data['current_humidity']
        device_statuses = self.get_air_quality_entities(room)

        remove_priority = [device for device, status in device_statuses.items() if not bool(status)]

        # Get last priority device
        last_priority_device = self.priority_devices[room]['device']
        last_priority_time = self.priority_devices[room]['time']

        # Check if priority device has been on for less than 10 minutes
        time_check = (datetime.now() - last_priority_time) < timedelta(seconds=self.args.get('priority_time', 600))

        # Get Priority Device Activation Data
        priority_device = self.automations.get_matching_entities(
            area=room,
            domain='input_text',
            pattern=f'air_quality_priority_device$',
            get_attribute='timedelta',
            device_state=f'{last_priority_device}'
        )
        try:
            exceptions = {
                'purifier': pm2_5 > 100,
                'humidifier': current_humidity < 25 or current_humidity > 75,
            }
        except Exception as e:
            self.log(
                f"""
                    In decide_device_activation - {room}:
                    Error: {e}
                    PM2.5: {pm2_5}
                    Humidity: {current_humidity}
                """,
                level='INFO',
            )

        if time_check:
            if pm2_5 < 100 and 45 <= current_humidity <= 60:
                self.log(
                    f"""
                        In decide_device_activation - {room}:
                        Priority Device {last_priority_device} has been on for less than 10 minutes. Not resetting 
                        priority.
                        {pm2_5:.1f} ug/m3, Humidity: {current_humidity:.1f}%
                    """,
                    level='INFO',
                )

                return last_priority_device
            else:

                for exception, condition in exceptions.items():
                    debounce_key = f'{room}_exception'
                    if self.should_debounce(debounce_key):
                        return last_priority_device

                    if exception != last_priority_device and condition:
                        self.log(
                            f"""
                                In decide_device_activation - {room}:
                                PM2.5: {pm2_5:.1f} ug/m3, Humidity: {current_humidity:.1f}%
                                Priority Device {last_priority_device} has been on for less than 10 minutes. But pm2.5 
                                or humidity has exceeded safety threshold. Resetting priorities. 
                                
                                Changing priority to from {last_priority_device} to {exception}
                            """,
                            level='INFO',
                        )
                        return exception
                return last_priority_device

        else:
            self.log(
                f"""
                    In decide_device_activation - {room}:
                    Priority Device {last_priority_device} has been on for more than 10 minutes. Resetting priority.
                    {priority_device}
                """,
                level='INFO',
            )

        # Calculate dynamic priorities
        priorities = self.calculate_dynamic_priority(
            room=room,
            pm2_5=pm2_5,
            current_humidity=current_humidity,
            weighting='weighted'
        )

        # Remove the priority status for non-existent devices
        for priority in remove_priority:
            priorities.pop(priority)

        if priorities:
            # Get the device with the highest priority
            highest_priority_device = max(priorities, key=priorities.get)

            self.update_air_quality_entities_for_room(
                room,
                highest_priority_device,
                pm2_5,
                current_humidity,
                priorities,
                priorities[highest_priority_device]
            )
            self.log(f"Returning highest priority device: {highest_priority_device}")

            if last_priority_device != highest_priority_device:
                self.priority_devices[room] = {'device': highest_priority_device, 'time': datetime.now()}

            return highest_priority_device

        self.log(
            f"""
                In decide_device_activation - {room}:
                NOTHING TO ACTIVATE
                Priorities: {priorities} 
            """,
            level='DEBUG',
        )

        return None

    def calculate_dynamic_priority(self, room, pm2_5, current_humidity, weighting='sum'):
        priorities = {'purifier': 0, 'humidifier': 0, 'oil_diffuser': .5}
        # Get dynamic priorities

        device_state = 'off'
        last_inactive_times = self.automations.get_matching_entities(
            area=room,
            domain=['humidifier', 'fan'],
            pattern=['humidifier$', 'oil_diffuser$', 'purifier$'],
            get_attribute='timedelta', device_state=device_state, persist=True
        )
        # last_inactive_times = last_inactive_times if last_inactive_times else {}

        # Time-weighted priority
        for device, last_active in last_inactive_times.items():
            time_weight = last_active['timedelta'].total_seconds() / 3600  # Time since being on/off
            is_device_still = last_active['persist']  # Check if device is still on/off
            time_weight = time_weight if is_device_still else 0

            if 'purifier' in device:
                priorities['purifier'] += self.automations.calculate_individual_score(time_weight, 1, 'greater')

            elif 'oil_diffuser' in device:
                priorities['oil_diffuser'] += self.automations.calculate_individual_score(time_weight, 1, 'greater')

            elif 'humidifier' in device:
                priorities['humidifier'] += self.automations.calculate_individual_score(time_weight, 1, 'greater')

        # Priority rules (adjust based on actual requirements)
        purifier_score = self.automations.calculate_individual_score(pm2_5, 50, 'greater')
        humidity_score = self.automations.calculate_individual_score(current_humidity, 55, 'lower')

        purifier_time_score = priorities['purifier']
        humidity_time_score = priorities['humidifier']
        diffuser_time_score = priorities['oil_diffuser']

        if weighting == 'sum':
            priorities['purifier'] += purifier_score
            priorities['humidifier'] += humidity_score

        elif weighting == 'mean':
            priorities['purifier'] += purifier_score
            priorities['purifier'] /= 2

            priorities['humidifier'] += humidity_score
            priorities['humidifier'] /= 2

        elif weighting == 'weighted':
            priorities['purifier'] *= .40
            priorities['purifier'] += purifier_score * .60

            priorities['humidifier'] *= .40
            priorities['humidifier'] += humidity_score * .60

        self.log(
            f"""
                Dynamic Priority Scores for {room.title()}:
                PM2.5: {pm2_5:.1f} ug/m3, Humidity: {current_humidity:.1f}%
                    Sensor Scores:
                        Purifier: {purifier_score:.2f}
                        Humidifier: {humidity_score:.2f}

                    Time Scores:
                        Purifier: {purifier_time_score:.2f}
                        Humidifier: {humidity_time_score:.2f}
                        Diffuser: {diffuser_time_score:.2f}

                    Final Scores:
                        Purifier: {priorities['purifier']:.2f}
                        Humidifier: {priorities['humidifier']:.2f}
                        Diffuser: {priorities['oil_diffuser']:.2f}\n
                    """,
            level='DEBUG',
        )

        return priorities

    def diffuser_cycle_logic(self, *args, **kwargs):

        room = kwargs.get('room')
        if self.priority_devices[room]['device'] != 'oil_diffuser':
            self.diffuser_cycle_thread[room] = True
            return

        # Don't turn back on if it is in its cool off period
        if not self.diffuser_cycle_thread[room]:
            return

        # Get current grade level
        grade_level = int(float(self.get_state(f'input_number.{room}_oil_grade_level')))

        # Calculate time on and time off based on grade level
        if grade_level == 10:
            time_on = None  # Continuous operation
            time_off = 0
        else:
            time_on = int(float(self.get_state(f'input_number.oil_diffuser_time_on')))  # On for x seconds
            time_off = (10 - grade_level) * 60  # Off for (10 - grade_level) minutes

        # Turn on diffuser
        self.run_in(self.diffuser_cycle_on, 0, room=room)
        self.run_in(self.diffuser_cycle_off, time_on, room=room)
        self.run_in(self.diffuser_cycle_logic, time_on + time_off, room=room)

    def diffuser_cycle_off(self, *args, **kwargs):
        room = kwargs.get('room')
        self.diffuser_cycle_thread[room] = False
        if self.args.get('use_regex_matching', True):
            response = self.automations.command_matching_entities(
                hacs_commands='turn_off',
                area=room,
                domain='humidifier',
                pattern=self.args.get('regex_matching').get('devices').get('oil_diffuser', 'oil_diffuser$'),
                device_state='on'
            )
        else:
            oil_diffuser = self.get_air_quality_entities(room).get('oil_diffuser')
            response = self.automations.command_matching_entities(
                hacs_commands='turn_off',
                area=room,
                domain='humidifier',
                include_only=True,
                include_manual_entities=list(oil_diffuser.keys()),
                device_state='on'
            )

        humidifier_penalties = self.check_air_quality_mode_penalties('oil_diffuser')

        if any(humidifier_penalties):
            return

        if self.args.get('use_regex_matching', True):
            diffuser_light_entity = self.automations.command_matching_entities(
                hacs_commands='turn_on',
                area=room,
                domain='light',
                pattern=self.args.get('regex_matching').get('devices').get('oil_diffuser', 'oil_diffuser$').strip('$'),
                color_name='red',
                brightness=100
            )
        self.log(f"\n{room} - Diffuser Cycle OFF:\n{response}\n{diffuser_light_entity}\n", level="INFO")

    def diffuser_cycle_on(self, *args, **kwargs):
        room = kwargs.get('room')
        self.diffuser_cycle_thread[room] = True
        if self.priority_devices[room]['device'] != 'oil_diffuser':
            return

        if self.args.get('use_regex_matching', True):
            # Turn on diffuser
            response = self.automations.command_matching_entities(
                hacs_commands={
                    'turn_on': {},
                    'set_humidity': {'humidity': 100},
                },
                area=room,
                domain='humidifier',
                pattern=self.args.get('regex_matching').get('devices').get('oil_diffuser', 'oil_diffuser$'),
                device_state='off'
            )
        else:
            oil_diffuser = self.get_air_quality_entities(room).get('oil_diffuser')
            response = self.automations.command_matching_entities(
                hacs_commands={
                    'turn_on': {},
                    'set_humidity': {'humidity': 100},
                },
                area=room,
                domain='humidifier',
                include_only=True,
                include_manual_entities=list(oil_diffuser.keys()),
                device_state='off'
            )
        humidifier_penalties = self.check_air_quality_mode_penalties('oil_diffuser')

        if any(humidifier_penalties):
            return

        if self.args.get('use_regex_matching', True):
            diffuser_light_entity = self.automations.command_matching_entities(
                hacs_commands='turn_on',
                area=room,
                domain='light',
                pattern=self.args.get('regex_matching').get('devices').get('oil_diffuser', 'oil_diffuser$').strip('$'),
                color_name='green',
                brightness=100
            )
        self.log(f"\n{room} - Diffuser Cycle ON:\n{response}\n{diffuser_light_entity}\n", level="INFO")

    def get_fan_percentage(self, pm2_5):
        # Get thresholds and percentages from input_number entities.  These are set in the UI.
        iterate = ['low', 'medium_low', 'medium_high', 'high']
        thresholds = [float(self.get_state(f'input_number.thresholds_pm2_5_{i}')) for i in iterate]
        percentage = [float(self.get_state(f'input_number.percentage_pm2_5_{i}')) for i in iterate]

        for threshold, percentage in zip(thresholds, percentage):  # Iterate through thresholds and percentages
            if pm2_5 < threshold:  # If pm2.5 value is less than threshold, return percentage
                return percentage  # This will be the first percentage that is less than the pm2.5 value
        return 100

    def check_air_quality_mode_penalties(self, device_type, penalties=None):
        """Check if there are any penalties for the air quality mode."""
        global_penalties = {
            'eco_mode': self.get_state("input_select.house_mode") == 'Eco',
            'entertainment_mode': self.get_state("input_boolean.entertainment_mode") == 'on',
            'night_mode': self.get_state("input_select.house_mode") == 'Night',
        }

        custom_sleep_mode = {
            'sleep': 'sleep' in self.args.get('modes', False),
            'work': 'work' in self.args.get('modes', False),
        }
        penalties = global_penalties.update(penalties) if penalties else global_penalties
        if any(custom_sleep_mode.values()):
            for mode in custom_sleep_mode:
                for custom_condition in self.args['modes'][mode]:
                    entity_id = custom_condition.get('entity_id')
                    value = custom_condition.get('value')
                    device_types = custom_condition.get('device_types')
                    device_types = device_types if isinstance(device_types, list) else [device_types]

                    if value and device_type in device_types:
                        if isinstance(value, list) or isinstance(value, str):
                            value = value if isinstance(value, list) else [value]
                            penalties[entity_id] = self.get_state(entity_id) in value
                        else:
                            penalties[entity_id] = self.get_state(entity_id) == value

        return penalties

    def set_purifier_mode(self, room):
        app_name = 'air_quality'
        noise_intolerance = ['Commute', 'Sleep', 'Work']
        purifier_entity = self.get_air_quality_entities('room').get('purifier')
        fan_penalties = self.check_air_quality_mode_penalties('purifier')

        if any(fan_penalties.values()):
            self.log(
                msg=f"""
                    In set_purifier_mode - {room}:
                    Setting Sleep Mode purifier
                    """,
                level='INFO',
            )
            self.call_service("fan/set_preset_mode", entity_id=list(purifier_entity.keys()), preset_mode='sleep')
            return

        else:
            return True

    def set_humidifier_mode(self, room):
        app_name = 'air_quality'
        noise_intolerance = ['Commute', 'Sleep']
        humidifier_entities = self.get_air_quality_entities('room').get('humidifier')

        humidifier_penalties = self.check_air_quality_mode_penalties('humidifier')

        if any(humidifier_penalties.values()) and room != 'bedroom':
            self.log(
                f"""
                    In set_humidifier_mode - {room}:
                    Setting Sleep Mode for the Humidifier
                    """,
                level='INFO',
            )
            self.call_service("humidifier/set_mode", entity_id=list(humidifier_entities.keys()), mode='sleep')
            return
        elif any(humidifier_penalties.values()) and room == 'bedroom':
            self.log(
                msg=f"""
                    In set_humidifier_mode - {room}:
                    Setting Baby Mode for the Humidifier
                    """,
                level='INFO',
            )
            self.call_service("humidifier/set_mode", entity_id=list(humidifier_entities.keys()), mode='baby')
            return

        else:
            self.call_service("humidifier/set_mode", entity_id=list(humidifier_entities.keys()), mode='manual')
            return True

    def set_diffuser_mode(self, room):
        return True

    def update_air_quality_entities_for_room(self, room, priority_device, pm2_5, humidity, time_score, weight_score):
        """Update the Air Quality entities in Home Assistant for a specific room."""
        self.log(
            f"""
                    Entering update_air_quality_entities_for_room - {room}
                    The priority device is {priority_device}
                    The PM2.5 is {pm2_5}
                    The Humidity is {humidity}
            """,
            level='DEBUG',
        )

        # Rounding priority device scores to two decimals and converting to percentage as a string
        viewable_string = ''
        for device, score in time_score.items():
            viewable_string += f"{device}: {score:.2%}\t"

        self.set_state(f"input_text.{room}_air_quality_priority_device", state=priority_device)
        self.set_state(f"input_text.{room}_air_quality_pm", state=str(pm2_5))
        self.set_state(f"input_text.{room}_air_quality_humidity", state=str(humidity))
        self.set_state(f"input_text.{room}_air_quality_time_score", state=viewable_string)
        self.set_state(f"input_text.{room}_air_quality_weight_score", state=str(weight_score))

        self.set_state(f"input_number.{room}_air_quality_pm", state=f"{pm2_5:,.0f}")
        self.set_state(f"input_number.{room}_air_quality_humidity", state=f"{humidity:,.0f}")
        self.set_state(f"input_number.{room}_air_quality_purifier_score", state=f"{time_score.get('purifier', 0):,.2f}")
        self.set_state(f"input_number.{room}_air_quality_humidifier_score",
                       state=f"{time_score.get('humidifier', 0):,.2f}")
        self.set_state(f"input_number.{room}_air_quality_oil_diffuser_score",
                       state=f"{time_score.get('oil_diffuser', 0):,.2f}")

    def should_debounce(self, debounce_key):
        """Check if the call should be debounced."""
        current_time = datetime.now()
        last_run = self.debounce_timers.get(debounce_key)

        if last_run is None:
            # If it's the first run, do not debounce
            self.debounce_timers[debounce_key] = current_time
            return False

        if current_time - last_run < self.debounce_period:
            # If we're within the debounce period, skip this call
            return True

        # If we're outside the debounce period, proceed with the call
        self.debounce_timers[debounce_key] = current_time
        return False

