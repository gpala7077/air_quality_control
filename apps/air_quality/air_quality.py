import appdaemon.plugins.hass.hassapi as hass
from datetime import datetime, timedelta, time
import numpy as np
import pandas as pd
import pytz
from smarthome_global_v2 import *


class AirQuality(Base):
    """AirQuality class. """

    def initialize(self):
        """Initialize the HACS app."""
        self.app_name = "Adaptive Air Quality Priority System"
        super().initialize()  # Initialize the Base class
        self.run_in(
            self.generate_logging_cards,
            delay=10,
        )

    def setup(self):
        super().setup()
        self.define_automation_boolean_checks()
        self.warning_thresholds = {
            'pm2_5': {'low': 0, 'high': 100},
            'humidity': {'low': 30, 'high': 70},
            'temperature': {'low': 32, 'high': 80},  # Fahrenheit
            'co2': {'low': 0, 'high': 1000},  # ppm
            'voc': {'low': 0, 'high': 500},  # ppb
            'methane': {'low': 0, 'high': 50},  # ppm
            'carbon_monoxide': {'low': 0, 'high': 10},  # ppm
            'nitrogen_dioxide': {'low': 0, 'high': 100},  # ppb
            'ethanol': {'low': 0, 'high': 100},  # ppm
            'hydrogen': {'low': 0, 'high': 100},  # ppm
            'ammonia': {'low': 0, 'high': 50},  # ppm
            'nox': {'low': 0, 'high': 50},  # ppm
            'air_pressure': {'low': 0, 'high': 1000}  # hPa
        }
        warning_entities = {}
        group_dict = {
            "Warning Thresholds Low": [],
            "Warning Thresholds High": []
        }
        for sensor, config in self.warning_thresholds.items():
            for threshold, val in config.items():
                warning_entities[f'warning_thresholds_{sensor}_{threshold}'] = {
                    'level': 'home',
                    'attributes': {
                        "min": 0,
                        "max": val * 2 if val > 0 else 5,
                        "step": 1
                    },
                    'sync_mode': 'less',
                }
                group_dict[f"Warning Thresholds {threshold.title()}"].append(
                    f'input_number.warning_thresholds_{sensor}_{threshold}')

        self.call_service(
            service='pyscript/add_custom_dashboard_group',
            app_name=self.app_name_short,
            group_dict=group_dict
        )

        self.app_user_settings = {
            'input_numbers': {
                **warning_entities,
                'oil_diffuser_time_off': {
                    'level': 'room',
                    'initial_value': 10,
                    'attributes': {
                        "min": 1,
                        "max": 120,
                        "step": 1
                    },
                    'sync_mode': 'less',
                },
                'oil_diffuser_time_on': {
                    'level': 'room',
                    'initial_value': 60,
                    'attributes': {
                        "min": 1,
                        "max": 120,
                        "step": 1
                    },
                    'sync_mode': 'less',
                },
                'humidity_tolerance': {
                    'level': 'room',
                    'initial_value': 60,
                    'attributes': {
                        "min": 1,
                        "max": 100,
                        "step": 1
                    },
                    'sync_mode': 'less',
                },
                'humidity_target': {
                    'level': 'room',
                    'initial_value': 60,
                    'attributes': {
                        "min": 1,
                        "max": 100,
                        "step": 1
                    },
                    'sync_mode': 'less',
                },
                'thresholds_pm25_low': {
                    'level': 'room',
                    'initial_value': 10,
                    'attributes': {
                        "min": 0,
                        "max": 500,
                        "step": 1
                    },
                    'sync_mode': 'less',
                },
                'thresholds_pm25_medium_low': {
                    'level': 'room',
                    'initial_value': 50,
                    'attributes': {
                        "min": 0,
                        "max": 500,
                        "step": 1
                    },
                    'sync_mode': 'less',
                },
                'thresholds_pm25_medium_high': {
                    'level': 'room',
                    'initial_value': 70,
                    'attributes': {
                        "min": 0,
                        "max": 500,
                        "step": 1
                    },
                    'sync_mode': 'less',
                },
                'thresholds_pm25_high': {
                    'level': 'room',
                    'initial_value': 100,
                    'attributes': {
                        "min": 0,
                        "max": 500,
                        "step": 1
                    },
                    'sync_mode': 'less',
                },
                'percentage_pm25_low': {
                    'level': 'room',
                    'initial_value': 25,
                    'attributes': {
                        "min": 0,
                        "max": 500,
                        "step": 1
                    },
                    'sync_mode': 'less',
                },
                'percentage_pm25_medium_low': {
                    'level': 'room',
                    'initial_value': 50,
                    'attributes': {
                        "min": 0,
                        "max": 500,
                        "step": 1
                    },
                    'sync_mode': 'less',
                },
                'percentage_pm25_medium_high': {
                    'level': 'room',
                    'initial_value': 75,
                    'attributes': {
                        "min": 0,
                        "max": 500,
                        "step": 1
                    },
                    'sync_mode': 'less',
                },
                'percentage_pm25_high': {
                    'level': 'room',
                    'initial_value': 100,
                    'attributes': {
                        "min": 0,
                        "max": 500,
                        "step": 1
                    },
                    'sync_mode': 'less',
                },
            },
            'input_texts': {
                'air_quality_priority_device': {'level': 'room', 'initial_value': 'oil_diffuser'},
            }
        }

        self.turn_off_logic = {
            'purifier': self.turn_off_purifier,
            'humidifier': self.turn_off_humidifier,
            'oil_diffuser': self.turn_off_diffuser,
            'fan': self.turn_off_fan
        }
        self.turn_on_logic = {
            'purifier': self.turn_on_purifier,
            'humidifier': self.turn_on_humidifier,
            'oil_diffuser': self.turn_on_diffuser,
            'fan': self.turn_on_fan
        }
        self.continue_logic = {
            'purifier': self.set_purifier_mode,
            'humidifier': self.set_humidifier_mode,
            'oil_diffuser': self.set_diffuser_mode,
            'fan': self.set_fan_mode,
        }
        self.cron_job_funcs = {
            'air_circulation': self.circulate_air_logic,
            'humidify': self.humidify_logic,
            'deodorize_and_refresh': self.deodorize_and_refresh_logic,
        }
        self.diffuser_cycle_thread = {}
        self.user_room_auto = False
        self.master_air_quality_thread = {}
        self.empty_tank_listener = {}
        self.priority_devices = {}
        self.master_off_kwargs = dict(
            include_priority=True,
            check_for_occupancy=True
        )
        self.monitor_co2_levels()


    def define_automation_boolean_checks(self):
        """Define the dynamic conditions for the automation"""
        self.automation_boolean_checks = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(dict))))
        self.room_automation_booleans = {}
        # Iterate through every area
        for room_config in self.areas:
            room_id = room_config['area_id']
            room_name = room_config['name']
            floor_id = room_config['floor_id']
            for master_onoff in ['on', 'off']:
                # Create Latency variable for research
                sensor_name = f"{room_name.title()} {self.app_name_short.replace('_', ' ').title()} {master_onoff.title()} Latency"
                self.run_in(
                    self.call_service,
                    delay=self.time_to_delay_start,
                    service='pyscript/create_template_sensor',
                    sensor_name=sensor_name,
                    state='',
                    app_name=self.app_name_short,
                    attributes={
                        "unit_of_measurement": 'seconds'
                    }
                )

            # Iterate through every device type
            for device_type in self.device_types:
                if device_type == 'switches':
                    continue

                d_type = device_type.rstrip('s')
                delay_off = self.get_delay_off(room_id)

                if not self.controllable[room_id][device_type]['all']:
                    continue
                # Define General Light Boolean On and Off Conditions (Bright or Dark not general)
                boolean_check = {
                    'on': {
                        'master_and_user_overrides': ' and '.join([
                            f"is_state('input_boolean.automatic_{device_type}', 'on')",
                            f"is_state('input_boolean.{room_id}_{d_type}_auto', 'on')",
                        ]),
                        'is_anyone_home': ' or '.join([
                            "is_state('sensor.global_users','home')",
                            "is_state('input_boolean.guest_mode', 'on')",
                        ]),
                        'is_room_occupied': f"is_state('binary_sensor.{room_id}_occupancies', 'on')",
                    },
                    'off': {
                        'master_and_user_overrides': ' and '.join([
                            f"is_state('input_boolean.automatic_{device_type}', 'on')",
                            f"is_state('input_boolean.{room_id}_{d_type}_auto', 'on')",
                        ]),
                        'is_room_not_occupied': ' and '.join([
                            f"is_state('binary_sensor.{room_id}_occupancies', 'off')",
                        ]),
                    },
                }

                # Iterate through Master On/Off
                for master_onoff in ['on', 'off']:
                    entity_id = f'binary_sensor.{room_id}_{self.app_name_short}_{device_type}_{master_onoff}_conditions'

                    attributes = boolean_check[master_onoff].copy()
                    attributes.update({
                        'last_triggered': f"states('sensor.{room_id}_{self.app_name_short}_{device_type}_{master_onoff}_last_triggered')",
                        'latency': f"states('sensor.{room_id}_{self.app_name_short}_{master_onoff}_latency')",
                        'humidifier': f"states('input_number.{room_id}_air_quality_humidifier_score')",
                        'purifier': f"states('input_number.{room_id}_air_quality_purifier_score')",
                        'oil_diffuser': f"states('input_number.{room_id}_air_quality_oil_diffuser_score')",
                        'fan': f"states('input_number.{room_id}_air_quality_fan_score')",
                        'priority_device': f"states('input_text.{room_id}_air_quality_priority_device')",
                        'warnings': f"states('sensor.{room_id}_{self.app_name_short}_warnings')",
                        'air_circulation': f"states('sensor.{room_id}_{self.app_name_short}_air_circulation')",
                        'deodorize_and_refresh': f"states('sensor.{room_id}_{self.app_name_short}_deodorize_and_refresh')",
                        'humidify': f"states('sensor.{room_id}_{self.app_name_short}_humidify')",
                    })

                    # Send YAML template to pyscript for creation
                    self.run_in(
                        self.call_service,
                        delay=self.time_to_delay_start,
                        service='pyscript/create_binary_sensor',
                        binary_sensor_name=entity_id,
                        associated_sensors=boolean_check[master_onoff],
                        device_type='occupancy',
                        device_class='motion',
                        app_name=self.app_name_short,
                        attributes={key: "{{" + val + "}}"  for key, val in attributes.items()},
                        as_group=False,
                        logic=' and ',
                    )
                    self.room_automation_booleans[entity_id] = room_id

    def master_on(self, *args, **kwargs):

        room = kwargs.get('room')
        override = kwargs.get('override', False)
        controllable = kwargs.get('controllable', self.get_entities(room))
        occupancy_sensors = kwargs.get('occupancy', self.room_sensor_entities[room]['occupancy'])
        master_conditions =  kwargs.get('master_conditions')

        priority_devices = self.decide_device_activation(room)
        if not priority_devices:
            return
        priority_devices = priority_devices if isinstance(priority_devices, list) else [priority_devices]

        for priority_device in priority_devices:
            priority_device_plural = pluralize(priority_device)

            if master_conditions.get(f"{priority_device_plural}_on") == 'off':
                self.log_success_block(
                    booleans={},
                    room=room,
                    success=False,
                    master_on_off='on_conditions',
                )
                continue

            # Check mode and set device accordingly
            continue_with_automation = self.continue_logic.get(priority_device, lambda x: False)(room)
            if continue_with_automation:  # If mode behavior was triggered. Don't continue air quality logic

                self.log_info(
                    message=f"""
                        In air_quality_logic - {room}:
                        The priority device is {priority_device}.
                        Turning on all {priority_device}s.
                    """,
                    level='INFO',
                    log_room=room,
                    function_name='master_on'
                )
                self.log_success_block(
                    booleans={},
                    room=room,
                    success=True,
                    master_on_off='on_conditions',
                )

                # Turn on the device
                self.run_in(
                    self.turn_on_logic[priority_device],
                    delay=0,
                    room=room,
                )

        # Turn off other devices
        self.run_in(
            self._master_off,
            delay=0,
            **kwargs,
            include_priority=False
        )
        return True

    def master_off(self, *args, **kwargs):
        room = kwargs.get('room')
        check_for_occupancy = kwargs.get('check_for_occupancy', False)
        include_priority = kwargs.get('include_priority', False)
        priority_device = self.priority_devices.get(room, {}).get('device', 'purifier')
        priority_device = priority_device if isinstance(priority_device, list) else [priority_device]
        master_conditions =  kwargs.get('master_conditions')

        # Turn off devices
        for other_device, other_func in self.turn_off_logic.items():
            other_device_plural = pluralize(other_device)
            conditions = {
                'include_priority': include_priority and other_device in priority_device,
                'automation_boolean_checks': master_conditions.get(f"{other_device_plural}_off") == 'on',
                'not_include_priority': not include_priority and other_device not in priority_device
            }
            if (conditions['automation_boolean_checks'] and
                    (conditions['include_priority'] or conditions['not_include_priority'])):
                self.turn_off_logic[other_device](room=room)
                self.log_success_block(
                    booleans={},
                    room=room,
                    success=True,
                    master_on_off='off_conditions',
                )

            elif not conditions['automation_boolean_checks']:
                self.log_success_block(
                    booleans={},
                    room=room,
                    success=False,
                    master_on_off='off_conditions',
                )
        return True

    def turn_off_diffuser(self, room, **kwargs):
        debounce_key = f'{room}_turn_off_diffuser'
        if self.should_debounce(debounce_key):
            return

        if self.diffuser_cycle_thread.get(room):
            self.cancel_sequence(self.diffuser_cycle_thread[room])
            self.diffuser_cycle_thread[room] = None

    def turn_off_humidifier(self, room, **kwargs):
        debounce_key = f'{room}_turn_off_humidifier'
        if self.should_debounce(debounce_key):
            return

        include_patterns, use_groups = self.get_patterns('humidifiers', 'devices')
        response = self.controller.command_matching_entities(
            identity_kwargs=self.app_name_short,
            hacs_commands='turn_off',
            area=room,
            domain='humidifier',
            **include_patterns,

        )
        if response:
            self.log_info(
                message=f"""
                    In air_quality_logic - {room}:
                    Turning off humidifier.
                    {response}
                    """,
                level='DEBUG',
                log_room=room,
                function_name='turn_off_humidifier'
            )

    def turn_off_purifier(self, room, **kwargs):

        debounce_key = f'{room}_turn_off_purifier'
        if self.should_debounce(debounce_key):
            return

        include_patterns, exclude_patterns = self.get_patterns('purifiers', 'devices')

        response = self.controller.command_matching_entities(
            identity_kwargs=self.app_name_short,
            hacs_commands='turn_off',
            area=room,
            domain='fan',
            **include_patterns
        )
        if response:
            # Set fan percentage
            self.log_info(
                message=f"""
                    In air_quality_logic - {room}:
                    Turning off purifier.
                    {response}
                    """,
                level='DEBUG',
                log_room=room,
                function_name='turn_off_purifier'
            )

    def turn_off_fan(self, room, **kwargs):
        debounce_key = f'{room}_turn_off_fan'
        if self.should_debounce(debounce_key):
            return

        include_patterns, use_groups = self.get_patterns('fans', 'devices')
        response = self.controller.command_matching_entities(
            identity_kwargs=self.app_name_short,
            hacs_commands='turn_off',
            area=room,
            domain='fan',
            **include_patterns,
            device_state=['off', 'unavailable']
        )

        if response:
            self.log_info(
                message=f"""
                    In air_quality_logic - {room}:
                    Turning off fan.
                    {response}
                    """,
                level='DEBUG',
                log_room=room,
                function_name='turn_off_fan'
            )

    def execute_turn_off_command(self, room, debounce_key, check_for_occupancy=False):

        if self.should_debounce(debounce_key):
            return False

        if room is None:
            return False

        if self.manager.is_room_occupied(room) and check_for_occupancy:
            self.log_info(
                message=f"{room.title()} is still in use. Exiting...",
                level='INFO',
                log_room=room,
                function_name='execute_turn_off_command'
            )
            return False

        return True

    def turn_on_diffuser(self, room, **kwargs):
        bad_states = ['None', None, 'unknown','unavailable']
        debounce_key = f'{room}_turn_on_diffuser'
        master_conditions = self.get_master_conditions(room, master_onoff='on')
        master_conditions = master_conditions.get('oil_diffusers_on') == 'on'
        current_priority = self.priority_devices.get(room).get('device')

        # Only de-bounces non-cycling (non-recursive calls)
        if self.should_debounce(debounce_key) and kwargs.get('cycling') is None:
            return

        # Only proceed with function if oil diffuser is still the priority device and if conditions are still valid
        if current_priority != 'oil_diffuser' or not master_conditions:
            return

        # If this is a recursive-call, clear the sequence handle (since it is complete)
        if kwargs.get('cycling'):
            self.diffuser_cycle_thread[room] =  None


        oil_diffusers = list(self.controllable[room]['oil_diffusers']['all'].keys())
        lights = list(self.controller.get_matching_entities(
            area=room,
            domain='light',
            pattern='oil_diffuser'
        ).keys())

        time_off = self.get_state(f'input_number.{room}_oil_diffuser_time_off')  # On for x seconds
        time_on = self.get_state(f'input_number.{room}_oil_diffuser_time_on')  # On for x seconds
        time_on = int(float(time_on)) if time_on not in bad_states else 10  # On for x seconds
        time_off = int(float(time_off)) if time_off not in bad_states else 10  # On for x seconds


        oil_diffuser_sequence = [
                {'humidifier/turn_on': {'entity_id': oil_diffusers}},
                {'humidifier/set_humidity': {'entity_id': oil_diffusers, 'humidity': 100}},
                {'light/turn_on': {'entity_id': lights, 'color_name': 'green', 'brightness_pct': 100}},
                {'sleep': time_on},
                {'light/turn_on': {'entity_id': lights, 'color_name': 'red', 'brightness_pct': 100}},
                {'humidifier/turn_off': {'entity_id': oil_diffusers}},
                {'sleep': time_off},
        ]

        if self.diffuser_cycle_thread.get(room) is None:
            self.log_info(
                message=f"{room.title()} Diffuser cycle is Run",
                level='DEBUG_3',
                log_room=room,
                function_name='diffuser_cycle_logic'
            )
            self.diffuser_cycle_thread[room] = self.run_sequence(sequence=oil_diffuser_sequence)
            self.run_in(self.turn_on_diffuser, delay=time_on+time_off+1, room=room, cycling=True)

        elif self.diffuser_cycle_thread[room]:
            self.log_info(
                message=f"{room.title()} Diffuser cycle is already running. Exiting...",
                level='DEBUG_3',
                log_room=room,
                function_name='diffuser_cycle_logic'
            )
            return

    def turn_on_humidifier(self, room, **kwargs):
        debounce_key = f'{room}_turn_on_humidifier'
        if self.should_debounce(debounce_key):
            return

        humidity_tolerance = float(self.get_state(f"input_number.{room}_humidity_tolerance"))
        humidity_target = float(self.get_state(f"input_number.{room}_humidity_tolerance"))
        humidity = self.room_sensor_data[room]['humidity']

        if humidity <= humidity_tolerance:
            include_patterns, use_groups = self.get_patterns('humidifiers', 'devices')
            response = self.controller.command_matching_entities(
                hacs_commands={
                    'turn_on': {},
                    'set_mode': {'mode': 'manual'},
                    'set_humidity': {'humidity': humidity_target}
                },
                area=room,
                domain='humidifier',
                **include_patterns,
                device_state=['off', 'unavailable']
            )
            if response:
                entities = response['humidifier'].get('entities')
                for entity in entities:
                    self.run_in(self.is_empty, 0, device=entity, room=room)

                self.log_info(
                    message=f"""
                        In humidifier_logic - {room}:
                        Turning on humidifier.
                        {response}
                    """,
                    level='DEBUG',
                    log_room=room,
                    function_name='turn_on_humidifier'
                )

            else:
                self.log_info(
                    message=f"""
                        In humidifier_logic - {room}:
                        Humidifier is already on.
                    """,
                    level='DEBUG',
                    log_room=room,
                    function_name='turn_on_humidifier'
                )

    def turn_on_purifier(self, room, **kwargs):
        debounce_key = f'{room}_turn_on_purifier'
        if self.should_debounce(debounce_key):
            return

        pm2_5 = self.room_sensor_data[room]['pm2_5']
        fan_percentage = self.get_fan_percentage(room, pm2_5)  # Get fan percentage based on pm2.5 value
        include_patterns, use_groups = self.get_patterns('purifiers', 'devices')

        response = self.controller.command_matching_entities(
            identity_kwargs=self.app_name_short,
            hacs_commands={
                'turn_on': {},
                'set_percentage': {'percentage': fan_percentage}
            },
            area=room,
            domain='fan',
            **include_patterns,
            device_state=['off', 'unavailable']
        )

        if response:
            # Set fan percentage
            self.log_info(
                message=f"""
                    In air_quality_logic - {room}:
                    Setting fan percentage to {fan_percentage}%
                    {response}
                    """,
                level='DEBUG',
                log_room=room,
                function_name='turn_on_purifier'
            )

    def turn_on_fan(self, room, **kwargs):
        debounce_key = f'{room}_turn_on_fan'
        if self.should_debounce(debounce_key):
            return

        include_patterns, use_groups = self.get_patterns('fans', 'devices')
        response = self.controller.command_matching_entities(
            identity_kwargs=self.app_name_short,
            hacs_commands='turn_on',
            area=room,
            domain='fan',
            **include_patterns,
            device_state=['off', 'unavailable']
        )

        if response:
            self.log_info(
                message=f"""
                    In air_quality_logic - {room}:
                    Turning on fan.
                    {response}
                    """,
                level='DEBUG',
                log_room=room,
                function_name='turn_on_fan'
            )

            # Make sure to turn on oscillation if fan has oscillation feature
            response = self.controller.command_matching_entities(
                identity_kwargs=self.app_name_short,
                hacs_commands='oscillate',
                area=room,
                domain='fan',
                include_only=True,
                include_manual_entities=response['fan']['entities'],
                get_attribute='oscillating',
                device_state=lambda x: x['oscillating'] is not None,
                oscillating=True
            )

    def is_empty(self, *args, **kwargs):
        device = kwargs.get('device')
        room = kwargs.get('room')
        # Check if device has 'water_lacks' attribute and if it's True
        device_state = self.controller.get_matching_entities(
            domain='humidifier',
            include_only=True,
            include_manual_entities=[device],
            get_attribute='water_lacks',
        )
        water_lacks = device_state[device].get('water_lacks', False)
        if not pd.isna(water_lacks) and water_lacks:
            self.log_info(
                message=f"""
                    In is_empty - {device}:
                    Humidifier is empty. Informing User.
                    {device_state}
                """,
                level='INFO',
                log_room=room,
                function_name='humidifier_empty_callback'
            )
            return

        # Otherwise, rely on the existing logic of checking if device turns off within 3 seconds of being turned on.
        self.empty_tank_listener[device] = self.listen_state(
            self.humidifier_empty_callback,
            entity_id=device,
            old='on',
            new='off',
            oneshot=True,
            room=room
        )
        self.run_in(self._cancel_listen_state, 5, entity_id=device)

    def humidifier_empty_callback(self, *args, **kwargs):
        room = kwargs.get('room')
        self.log_info(
            message=f"""
                In humidifier_empty_callback - {args[0]}:
                Humidifier is empty. Informing User.
            """,
            level='INFO',
            log_room=room,
            function_name='humidifier_empty_callback'
        )

    def _cancel_listen_state(self, *args, **kwargs):
        entity_id = kwargs.get('entity_id')
        debounce_key = f'{entity_id}_cancel_listener'
        if self.should_debounce(debounce_key):
            return

        if self.empty_tank_listener[entity_id] is not None:
            self.cancel_listen_state(self.empty_tank_listener[entity_id])
            self.empty_tank_listener[entity_id] = None

    def humidify_logic(self, *args, **kwargs):
        debounce_key = f'air_quality_humidify'
        if self.should_debounce(debounce_key):
            return

        master_key = 'humidify'
        self.master_air_quality_thread[master_key] = True
        app_settings = self.get_current_app_settings()

        rooms = {
                room_config['area_id']: room_config['name']      # Iterate through every area
                for room_config in self.areas
            }
        # All boolean must be true in order to run Air Circulation Automation
        automation_boolean_checks = {
            'humidify': self.get_state("input_boolean.automatic_humidify") == 'on',
        }

        for area in rooms:
            self.set_state(
                entity_id=f"sensor.{area}_{self.app_name_short}_humidify",
                state='Running'
            )

            self.log_success_block(
                booleans=automation_boolean_checks,
                room=area,
                success=all(automation_boolean_checks.values()),
                master_on_off='on_conditions'
            )
            self.run_in(
                self.set_state,
                15 * 60,
                entity_id=f"sensor.{area}_{self.app_name_short}_humidify",
                state='Not Running'
            )

            self.priority_devices[area] = {'device': 'humidifier', 'time': datetime.now(self.timezone)}
            try:
                humidity_tolerance = float(self.get_state(f"input_number.{area}_humidity_tolerance"))
            except TypeError:
                humidity_tolerance = app_settings.get(f"input_number.{area}_humidity_tolerance", 60)

            try:
                humidity_target = float(self.get_state(f"input_number.{area}_humidity_target"))
            except TypeError:
                humidity_target = app_settings.get(f"input_number.{area}_humidity_target", 60)

            include_patterns, use_groups = self.get_patterns('humidifiers', 'devices')

            commands = [
                dict(
                    hacs_commands={
                        'turn_on': {},
                        'set_mode': {'mode': 'manual'},
                        'set_humidity': {'humidity': humidity_target}
                    },
                    domain='humidifier',
                    **include_patterns,
                    area=area,
                ),
            ]

            final_commands = [
                dict(
                    hacs_commands='turn_off',
                    domain='humidifier',
                    **include_patterns,
                    area=area
                )
            ]
            self.run_in(self._master_off, 0, room=area, include_priority=False)
            self.master_automation_logic(
                app_name='air_quality',
                task_id=f'humidify_{area}',
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
        master_key = 'deodorize_and_refresh'
        self.master_air_quality_thread[master_key] = True

        current_time = datetime.now(self.timezone)
        rooms = {
                room_config['area_id']: room_config['name']      # Iterate through every area
                for room_config in self.areas
            }        # All boolean must be true in order to run Air Circulation Automation
        automation_boolean_checks = {
            'deodorize_and_refresh': self.get_state("input_boolean.automatic_deodorize_and_refresh") == 'on',
        }

        for area in rooms:
            self.set_state(
                entity_id=f"sensor.{area}_{self.app_name_short}_deodorize_and_refresh",
                state='Running'
            )

            self.log_success_block(
                booleans=automation_boolean_checks,
                room=area,
                success=all(automation_boolean_checks.values()),
                master_on_off='on_conditions'
            )
            self.run_in(
                self.set_state,
                15 * 60,
                entity_id=f"sensor.{area}_{self.app_name_short}_deodorize_and_refresh",
                state='Not Running'
            )

            self.priority_devices[area] = {'device': 'oil_diffuser', 'time': current_time}
            include_patterns, use_groups = self.get_patterns('oil_diffusers', 'devices')
            commands = [
                dict(
                    hacs_commands={
                        'turn_on': {},
                        'set_humidity': {'humidity': 100}
                    },
                    domain='humidifier',
                    **include_patterns,
                    area=area,
                ),
                dict(
                    hacs_commands='turn_on',
                    domain='light',
                    pattern=[f'{pattern.strip("$")}$' for pattern in include_patterns],
                    color_name='purple',
                    brightness_pct=100,
                    area=area
                )

            ]

            final_commands = [
                dict(
                    hacs_commands='turn_off',
                    domain='humidifier',
                    **include_patterns,
                    area=area
                ),
                dict(
                    hacs_commands='turn_off',
                    domain='light',
                    pattern=[f'{pattern.strip("$")}$' for pattern in include_patterns],
                    area=area
                )
            ]

            self.run_in(self._master_off, 0, room=area, include_priority=True)
            self.master_automation_logic(
                app_name='air_quality',
                task_id=f'deodorize_and_refresh_{area}',
                master_name='deodorize_and_refresh',
                boolean_checks=automation_boolean_checks,
                commands=commands,
                final_commands=final_commands,
                default_wait=15 * 60,
                **kwargs
            )
        self.run_in(self.end_master_air_quality_thread, 15 * 60, master_key=master_key)

    def circulate_air_logic(self, *args, **kwargs):

        debounce_key = f'air_quality_circulate_air'
        master_key = 'circulate_air'
        if self.should_debounce(debounce_key):
            return

        self.master_air_quality_thread[master_key] = True

        # Any boolean must be true to run Air Circulation quietly
        sleep_mode_boolean_checks = self.check_air_quality_mode_penalties('purifier')
        # All boolean must be true in order to run Air Circulation Automation
        automation_boolean_checks = {
            'circulate_air': self.get_state("input_boolean.automatic_air_circulation") == 'on',
        }

        rooms = {
                room_config['area_id']: room_config['name']      # Iterate through every area
                for room_config in self.areas
            }

        for area in rooms:
            self.priority_devices[area] = {'device': 'purifier', 'time': datetime.now(self.timezone)}
            self.log_success_block(
                booleans=automation_boolean_checks,
                room=area,
                success=all(automation_boolean_checks.values()),
                master_on_off='on_conditions'
            )
            self.set_state(
                entity_id=f"sensor.{area}_{self.app_name_short}_circulate_air",
                state='Running'
            )
            self.run_in(
                self.set_state,
                15 * 60,
                entity_id=f"sensor.{area}_{self.app_name_short}_circulate_air",
                state='Not Running'
            )
            include_patterns, use_groups = self.get_patterns('purifiers', 'devices')
            include_fan_patterns, use_fan_groups = self.get_patterns('fans', 'devices')

            commands = [
                dict(
                    hacs_commands='turn_on',
                    domain='fan',
                    **include_patterns,
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
                    **include_patterns,
                    area=area
                ),

                dict(
                    hacs_commands='turn_on',
                    domain='fan',
                    **include_fan_patterns,
                    area=area
                ),
                dict(
                    hacs_commands={
                        'set_percentage': dict(percentage=25),
                        'set_preset_mode': dict(preset_mode='sleep')
                    } if any(sleep_mode_boolean_checks.values()) else {
                        'set_percentage': dict(percentage=100),
                        'set_preset_mode': dict(preset_mode='turbo')
                    },
                    domain='fan',
                    **include_fan_patterns,
                    area=area
                ),

            ]

            final_commands = [
                dict(
                    hacs_commands='turn_off',
                    domain='fan',
                    **include_patterns,
                    area=area
                ),
                dict(
                    hacs_commands='turn_off',
                    domain='fan',
                    **include_fan_patterns,
                    area=area
                )
            ]

            self.run_in(self._master_off, 0, room=area, include_priority=False)
            self.master_automation_logic(
                app_name='air_quality',
                task_id=f'air_circulation_{area}',
                master_name='air_circulation',
                boolean_checks=automation_boolean_checks,
                commands=commands,
                final_commands=final_commands,
                default_wait=15 * 60,
                **kwargs
            )
        hvac_fans = self.controller.get_matching_entities(
            domain='fan',
            pattern='hvac_fan$',
        )

        self.run_in(self.call_service, delay=0, service='fan/turn_on', entity_id=list(hvac_fans.keys()))
        self.run_in(self.call_service, delay=15 * 60, service='fan/turn_off', entity_id=list(hvac_fans.keys()))
        self.run_in(self.end_master_air_quality_thread, 15 * 60, master_key=master_key)

    def monitor_co2_levels(self):
        # Create automation that monitors Home CO2 levels
        group_co2 = self.controller.get_matching_entities(
            domain='sensor',
            pattern='co2s$',
        )
        for entity_id, entity_state in group_co2.items():
            self.listen_state(
                self.circulate_air_logic,
                entity_id=entity_id,
                new=lambda x: x not in ['unavailable', 'unknown', None, 'None'] and float(x) > 1100,
            )

    def end_master_air_quality_thread(self, *args, **kwargs):
        master_key = kwargs.get('master_key')
        self.master_air_quality_thread[master_key] = False

    def decide_device_activation(self, room):
        # Get Room Status
        sensor_data = self._get_sensor_data(room)
        # Air Particulate Data
        pm2_5 = sensor_data['pm2_5']

        # Humidity,  Temperature and Air Pressure Data
        humidity = sensor_data['humidity']
        temperature = sensor_data['temperature']
        air_pressure = sensor_data['air_pressure']

        # Gasses Data
        co2 = sensor_data['co2']
        voc = sensor_data['voc']
        methane = sensor_data['methane']
        carbon_monoxide = sensor_data['carbon_monoxide']
        nitrogen_dioxide = sensor_data['nitrogen_dioxide']
        ethanol = sensor_data['ethanol']
        hydrogen = sensor_data['hydrogen']
        ammonia = sensor_data['ammonia']

        self.log_info(
            message=f"""
                In decide_device_activation - {room}:
                PM2.5: {pm2_5}
                Humidity: {humidity}
                Temperature: {temperature}
                Air Pressure: {air_pressure}
                CO2: {co2}
                VOC: {voc}
                Methane: {methane}
                Carbon Monoxide: {carbon_monoxide}
                Nitrogen Dioxide: {nitrogen_dioxide}
                Ethanol: {ethanol}
                Hydrogen: {hydrogen}
                Ammonia: {ammonia}
            """,
            level='DEBUG',
            log_room=room,
            function_name='decide_device_activation'
        )
        warnings = self.check_warnings(room, sensor_data)

        device_statuses = self.get_entities(room)

        remove_priority = [device for device, status in device_statuses.items() if not bool(status)]

        # Get last priority device
        last_priority_device = self.priority_devices.get(room, {}).get('device', 'purifier')
        last_priority_time = self.priority_devices.get(room, {}).get('time', datetime.now(self.timezone))

        # Check if app just initialized
        app_initialized = self.get_time_until_ready()
        app_initialized = (last_priority_time - app_initialized) < timedelta(
            seconds=self.args.get('priority_time', 600))


        # Check if priority device has been on for less than 10 minutes
        time_check = (datetime.now(self.timezone) - last_priority_time) < timedelta(
            seconds=self.args.get('priority_time', 600))

        # Get Priority Device Activation Data
        priority_device = self.controller.get_matching_entities(
            area=room,
            domain='input_text',
            pattern=f'air_quality_priority_device$',
            get_attribute='timedelta',
            device_state=f'{last_priority_device}'
        )
        try:
            exceptions = {
                'purifier': pm2_5 > 100,
                'humidifier': humidity < 25 or humidity > 75,
            }
        except Exception as e:
            self.log_info(
                message=f"""
                    In decide_device_activation - {room}:
                    Error: {e}
                    PM2.5: {pm2_5}
                    Humidity: {humidity}
                """,
                level='DEBUG',
                log_room=room,
                function_name='decide_device_activation'
            )

        # Calculate dynamic priorities
        # priorities = self.calculate_dynamic_priority(
        #     room=room,
        #     pm2_5=pm2_5,
        #     humidity=humidity,
        #     weighting='weighted'
        # )
        priorities = self.calculate_dynamic_priority(
            room=room,
            sensor_data=sensor_data,
            weighting='weighted'
        )

        user_overrides = self.get_user_overrides()
        master_overrides = self.get_master_overrides()

        entity_overrides_user = []
        entity_overrides_master = []
        for priority in priorities:
            # Check if there are any user overrides
            for entity_id, entity_state in user_overrides[priority].items():
                if room in entity_id and entity_state.get('state') == 'off' and priority not in remove_priority:
                    remove_priority.append(priority)
                    entity_overrides_user.append(entity_id)

            # Check if there are any master overrides
            for entity_id, entity_state in master_overrides[priority].items():
                if entity_state.get('state') == 'off' and priority not in remove_priority:
                    remove_priority.append(priority)
                    entity_overrides_master.append(entity_id)

            if entity_overrides_user or entity_overrides_master:
                self.log_info(
                    message=f"""
                        In decide_device_activation - {room}:
                        {priority.title()} is disabled by user. Skipping Logic...

                        Disabled by User: {entity_overrides_user}
                        Disabled by Master: {entity_overrides_master}
                    """,
                    level='DEBUG',
                    function_name='decide_device_activation',
                    log_room=room
                )

        # Remove the priority status for non-existent devices
        for priority in remove_priority:
            priorities.pop(priority)

            # Get the device with the highest priority
            highest_priority_device = max(priorities, key=priorities.get)


            if last_priority_device != highest_priority_device:
                self.priority_devices[room] = {'device': highest_priority_device, 'time': datetime.now(self.timezone)}

            if time_check and not app_initialized:
                # If all warnings return as 'OK', then return the last priority device
                if all(warning['msg'] == 'OK' for warning in warnings.values()):
                    self.log_info(
                        message=f"""
                            In decide_device_activation - {room}:
                            Priority Device {last_priority_device} has been on for less than 10 minutes. Not resetting
                            priority.
                            {pm2_5:.1f} ug/m3, Humidity: {humidity:.1f}%
                        """,
                        level='INFO',
                        log_room=room,
                        function_name='decide_device_activation'
                    )
                    self.set_state(
                        entity_id=f"sensor.{room}_{self.app_name_short}_warning",
                        state='OK'
                    )

                    self.log_success_block(
                        booleans={'warnings': 'OK'},
                        room=room,
                        success=True,
                        master_on_off='on_conditions'
                    )

                    return last_priority_device
                else:
                    warnings_filtered = {key: value for key, value in warnings.items() if value['msg'] != 'OK'}
                    fans = self.controllable.get(room).get('fans').get('all')
                    purifiers = self.controllable.get(room).get('purifiers').get('all')
                    humidifiers = self.controllable.get(room).get('humidifiers').get('all')
                    oil_diffusers = self.controllable.get(room).get('oil_diffusers').get('all')

                    # Device prioritization based on warning types
                    for sensor, warning in warnings.items():
                        if warning['msg'] != 'OK':
                            # If particulate matter, CO2, or gases are high, return 'purifier'
                            if sensor in ['pm10', 'pm2_5', 'pm1', 'pm4', 'co2', 'carbon_monoxide', 'voc', 'methane',
                                          'nitrogen_dioxide', 'ammonia'] and (fans or purifiers):
                                self.log_info(
                                    message=f"""
                                        In decide_device_activation - {room}:
                                        {sensor.title()} exceeded threshold. Activating purifier and fan.
                                        {warning}
                                    """,
                                    level='INFO',
                                    log_room=room,
                                    function_name='decide_device_activation'
                                )
                                self.log_success_block(
                                    booleans={'warnings': f'{warnings_filtered}'},
                                    room=room,
                                    success=True,
                                    master_on_off='on_conditions'
                                )

                                self.priority_devices[room] = {'device': ['purifier', 'fan'],
                                                               'time': datetime.now(self.timezone)}
                                self.update_air_quality_entities_for_room(
                                    room,
                                    ['purifier', 'fan'],
                                    sensor_data,
                                    priorities,
                                    999
                                )
                                self.set_state(
                                    entity_id=f"sensor.{room}_{self.app_name_short}_warning",
                                    state=f'{warnings_filtered}'
                                )
                                self.log_info(
                                    message=f"Overridden Returning highest priority device: ['purifier', 'fan']",
                                    level='DEBUG',
                                    log_room=room,
                                    function_name='decide_device_activation'
                                )

                                return ['purifier', 'fan']

                            # If humidity is high, return 'humidifier'
                            elif sensor == 'humidity' and humidifiers:
                                if warning['high']:
                                    self.log_info(
                                        message=f"""
                                            In decide_device_activation - {room}:
                                            Humidity exceeded threshold. Activating humidifier.
                                            {warning}
                                        """,
                                        level='INFO',
                                        log_room=room,
                                        function_name='decide_device_activation'
                                    )
                                    self.log_success_block(
                                        booleans={'warnings': f'{warnings_filtered}'},
                                        room=room,
                                        success=True,
                                        master_on_off='on_conditions'
                                    )
                                    self.set_state(
                                        entity_id=f"sensor.{room}_{self.app_name_short}_warning",
                                        state=f'{warnings_filtered}'
                                    )
                                    self.priority_devices[room] = {'device': 'humidifier',
                                                                   'time': datetime.now(self.timezone)}
                                    self.update_air_quality_entities_for_room(
                                        room,
                                        'humidifier',
                                        sensor_data,
                                        priorities,
                                        999
                                    )

                                    self.log_info(
                                        message=f"Overridden Returning highest priority device: humidifier",
                                        level='DEBUG',
                                        log_room=room,
                                        function_name='decide_device_activation'
                                    )

                                    return 'humidifier'

                            # If temperature is high, return 'fan'
                            elif sensor == 'temperature' and fans:
                                if warning['high']:
                                    self.log_info(
                                        message=f"""
                                            In decide_device_activation - {room}:
                                            Temperature exceeded threshold. Activating fan.
                                            {warning}
                                        """,
                                        level='INFO',
                                        log_room=room,
                                        function_name='decide_device_activation'
                                    )
                                    self.log_success_block(
                                        booleans={'warnings': f'{warnings_filtered}'},
                                        room=room,
                                        success=True,
                                        master_on_off='on_conditions'
                                    )
                                    self.set_state(
                                        entity_id=f"sensor.{room}_{self.app_name_short}_warning",
                                        state=f'{warnings_filtered}'
                                    )
                                    self.priority_devices[room] = {'device': 'fan',
                                                                   'time': datetime.now(self.timezone)}

                                    self.update_air_quality_entities_for_room(
                                        room,
                                        'fan',
                                        sensor_data,
                                        priorities,
                                        999
                                    )

                                    self.log_info(
                                        message=f"Overridden Returning highest priority device: fan",
                                        level='DEBUG',
                                        log_room=room,
                                        function_name='decide_device_activation'
                                    )

                                    return 'fan'
                    return last_priority_device

            else:
                self.log_info(
                    message=f"""
                        In decide_device_activation - {room}:
                        Priority Device {last_priority_device} has been on for more than 10 minutes. Resetting priority.
                        {priority_device}
                    """,
                    level='DEBUG',
                    log_room=room,
                    function_name='decide_device_activation'
                )

            self.log_success_block(
                booleans={'warnings': 'Ok'},
                room=room,
                success=True,
                master_on_off='on_conditions'
            )
            self.set_state(
                entity_id=f"sensor.{room}_{self.app_name_short}_warning",
                state='OK'
            )
            self.update_air_quality_entities_for_room(
                room,
                highest_priority_device,
                sensor_data,
                priorities,
                priorities[highest_priority_device]
            )

            self.log_info(
                message=f"Returning highest priority device: {highest_priority_device}",
                level='DEBUG',
                log_room=room,
                function_name='decide_device_activation'
            )

            return highest_priority_device

        self.log_info(
            message=f"""
                In decide_device_activation - {room}:
                NOTHING TO ACTIVATE
                Priorities: {priorities}
            """,
            level='DEBUG',
            log_room=room,
            function_name='decide_device_activation'
        )

        return None

    def calculate_dynamic_priority(self, room, sensor_data, weighting='sum'):
        priorities = {'purifier': 0, 'humidifier': 0, 'oil_diffuser': 0.5, 'fan': 0}

        # Define device metrics mapping
        device_metrics = {
            'purifier': [
                'pm2_5',
                'co2',
                'voc',
                'methane',
                'carbon_monoxide',
                'nitrogen_dioxide',
                'ammonia'
            ],
            'humidifier': [
                'humidity'
            ],
            'fan': [
                'temperature',
                'co2',
                'voc',
                'carbon_monoxide',
            ],
            'oil_diffuser': []  # Assuming oil diffuser doesn't depend on air quality metrics
        }

        # Define optimal values and conditions for each metric
        optimal_values = {
            'pm2_5': 50,
            'co2': 1000,
            'voc': 500,
            'methane': 5,
            'carbon_monoxide': 9,
            'nitrogen_dioxide': 0.053,
            'ammonia': 0.25,
            'humidity': (40, 60),  # Optimal humidity range
            'temperature': (35, 80),  # Optimal temperature range in Fahrenheit
        }

        conditions = {
            'pm2_5': 'lower',
            'co2': 'lower',
            'voc': 'lower',
            'methane': 'lower',
            'carbon_monoxide': 'lower',
            'nitrogen_dioxide': 'lower',
            'ammonia': 'lower',
            'humidity': 'range',
            'temperature': 'range',
        }

        # Time-weighted priority
        include_fans_regex, use_groups = self.get_patterns('fans', 'devices')
        include_humidifiers_regex, use_groups = self.get_patterns('humidifiers', 'devices')
        include_purifiers_regex, use_groups = self.get_patterns('purifiers', 'devices')
        include_oil_diffusers_regex, use_groups = self.get_patterns('oil_diffusers', 'devices')

        last_fan_inactive_times = self.controller.get_matching_entities(
            area=room,
            domain='fan',
            **include_fans_regex,
            get_attribute='timedelta',
            device_state='off',
            persist=True
        )

        last_humidifier_inactive_times = self.controller.get_matching_entities(
            area=room,
            domain='humidifier',
            **include_humidifiers_regex,
            get_attribute='timedelta',
            device_state='off',
            persist=True
        )
        last_purifier_inactive_times = self.controller.get_matching_entities(
            area=room,
            domain='fan',
            **include_purifiers_regex,
            get_attribute='timedelta',
            device_state='off',
            persist=True
        )

        last_oil_diffuser_inactive_times = self.controller.get_matching_entities(
            area=room,
            domain='humidifier',
            **include_oil_diffusers_regex,
            get_attribute='timedelta',
            device_state='off',
            persist=True
        )

        #  Combine all inactive times
        last_inactive_times = {
            **last_fan_inactive_times,
            **last_humidifier_inactive_times,
            **last_purifier_inactive_times,
            **last_oil_diffuser_inactive_times
        }

        for device, last_active in last_inactive_times.items():
            time_weight = last_active['timedelta'].total_seconds() / 3600  # Time since being off in hours
            is_device_still_off = last_active['persist']  # Check if device is still off
            time_weight = time_weight if is_device_still_off else 0

            if 'purifier' in device:
                priorities['purifier'] += calculate_individual_score(
                    current_value=time_weight,
                    optimal_value=1,
                    condition='greater'
                )

            elif 'humidifier' in device:
                priorities['humidifier'] += calculate_individual_score(
                    current_value=time_weight,
                    optimal_value=1,
                    condition='greater'
                )
            elif 'fan' in device:
                priorities['fan'] += calculate_individual_score(
                    current_value=time_weight,
                    optimal_value=1,
                    condition='greater'
                )
            elif 'oil_diffuser' in device:
                priorities['oil_diffuser'] += calculate_individual_score(
                    current_value=time_weight,
                    optimal_value=1,
                    condition='greater'
                )

        # Sensor-based priority
        device_sensor_scores = {}
        for device, metrics in device_metrics.items():
            scores = []
            for metric in metrics:
                current_value = sensor_data.get(metric)
                optimal_value = optimal_values.get(metric)
                condition = conditions.get(metric)
                if (current_value is not None
                        and optimal_value is not None
                        and condition
                        and not pd.isna(current_value)
                ):
                    score = calculate_individual_score(
                        current_value=current_value,
                        optimal_value=optimal_value,
                        condition=condition
                    )
                    self.log_info(f"Sensor Score for {device} - {metric}: {score}")
                    scores.append(score)
            # Calculate average score for the device
            device_sensor_scores[device] = sum(scores) / len(scores) if scores else 0

        # Combine time-based and sensor-based scores
        for device in priorities.keys():
            sensor_score = device_sensor_scores.get(device, 0)
            time_score = priorities[device]

            if weighting == 'sum':
                priorities[device] += sensor_score
            elif weighting == 'mean':
                priorities[device] = (time_score + sensor_score) / 2
            elif weighting == 'weighted':
                priorities[device] = time_score * 0.4 + sensor_score * 0.6

            priorities[device] *= -1  # Invert the scores to prioritize the highest score
            self.log_info(f"Final Priority for {device}: {priorities[device]}")

        # Logging for debugging
        self.log_info(
            message=f"""
                Dynamic Priority Scores for {room.title()}:
                Sensor Data:
                    {', '.join([f"{metric.upper()}: {sensor_data.get(metric, 'N/A')}" for metric in sensor_data])}

                Sensor Scores:
                    {', '.join([f"{device.title()}: {device_sensor_scores[device]:.2f}" for device in device_sensor_scores])}

                Time Scores:
                    {', '.join([f"{device.title()}: {priorities[device]:.2f}" for device in priorities])}

                Final Priorities:
                    {', '.join([f"{device.title()}: {priorities[device]:.2f}" for device in priorities])}
                """,
            level='DEBUG',
            log_room=room,
            function_name='calculate_dynamic_priority'
        )

        return priorities

    def get_fan_percentage(self, room, pm2_5):
        # Create Purifier Settings:
        iterate = {
            "pm25_low",
            "pm25_medium_low",
            "pm25_medium_high",
            "pm25_high"
        }
        thresholds = []
        percentage = []
        for key in iterate:
            percent = self.get_state(f'input_number.{room}_percentage_{key}')
            percent = float(percent) if percent else None
            threshold = self.get_state(f'input_number.{room}_thresholds_{key}')
            threshold = float(threshold) if threshold else None
            if percent and threshold:
                thresholds.append(threshold)
                percentage.append(percent)

        for threshold, percentage in zip(thresholds, percentage):  # Iterate through thresholds and percentages
            if pm2_5 < threshold:  # If pm2.5 value is less than threshold, return percentage
                return percentage  # This will be the first percentage that is less than the pm2.5 value

        if thresholds and percentage:
            return 100
        else:
            return 0

    def check_air_quality_mode_penalties(self, device_type, penalties=None):
        """Check if there are any penalties for the air quality mode."""
        global_penalties = {
            'eco_mode': self.get_state("input_select.house_mode") == 'Eco',
            'entertainment_mode': self.get_state("input_boolean.entertainment_mode") == 'on',
            'night_mode': self.get_state("input_select.house_mode") == 'Night',
        }

        custom_sleep_mode = {
            'sleep': self.args.get('modes', {}).get('sleep', {}),
            'work': self.args.get('modes', {}).get('work', {}),
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
        purifier_entity = self.get_entities(room).get('purifier')
        fan_penalties = self.check_air_quality_mode_penalties('purifier')

        if any(fan_penalties.values()):
            self.log_info(
                message=f"""
                    In set_purifier_mode - {room}:
                    The priority device is purifier.
                    Encountered penalties for the purifier.
                    {fan_penalties}

                    Setting Sleep Mode purifier
                    """,
                level='INFO',
                log_room=room,
                function_name='set_purifier_mode'
            )
            self.call_service("fan/set_preset_mode", entity_id=list(purifier_entity.keys()), preset_mode='sleep')
            return

        else:
            return True

    def set_fan_mode(self, room):
        app_name = 'air_quality'
        purifier_entity = self.get_entities(room).get('fan')
        fan_penalties = self.check_air_quality_mode_penalties('fan')

        if any(fan_penalties.values()):
            # Make sure to turn on oscillation if fan has oscillation feature
            response1 = self.controller.command_matching_entities(
                identity_kwargs=self.app_name_short,
                hacs_commands='oscillate',
                area=room,
                domain='fan',
                include_only=True,
                include_manual_entities=list(purifier_entity.keys()),
                get_attribute='oscillating',
                device_state=lambda x: x['oscillating'] is not None,
                oscillating=True
            )
            # Make sure to set preset mode if fan has preset mode feature
            response2 = self.controller.command_matching_entities(
                identity_kwargs=self.app_name_short,
                hacs_commands='set_preset_mode',
                area=room,
                domain='fan',
                include_only=True,
                include_manual_entities=list(purifier_entity.keys()),
                get_attribute='preset_modes',
                device_state=lambda x: x['preset_modes'] is not None and 'sleep' in x['preset_modes'],
                preset_mode='sleep'
            )

            # If not response for set_preset_mode, then continue with regular fan automation
            if not response2:
                return True

            self.log_info(
                message=f"""
                    In set_fan_mode - {room}:
                    The priority device is fan.
                    Encountered penalties for the fan.
                    {fan_penalties}

                    Setting Sleep Mode fan
                    
                    Oscillate Response: {response1}
                    
                    Set Preset Mode Response: {response2}
                    """,
                level='INFO',
                log_room=room,
                function_name='set_fan_mode'
            )

            return

        else:
            return True

    def set_humidifier_mode(self, room):
        app_name = 'air_quality'
        humidifier_entities = self.get_entities(room).get('humidifier')
        humidifier_penalties = self.check_air_quality_mode_penalties('humidifier')

        if any(humidifier_penalties.values()) and room != 'bedroom':
            self.log_info(
                message=f"""
                    In set_humidifier_mode - {room}:
                    The priority device is humidifier.
                    Encountered penalties for the humidifier.
                    {humidifier_penalties}
                    Setting Sleep Mode for the Humidifier
                    """,
                level='INFO',
                log_room=room,
                function_name='set_humidifier_mode'
            )
            self.call_service("humidifier/set_mode", entity_id=list(humidifier_entities.keys()), mode='sleep')

            for entity in humidifier_entities:
                self.run_in(self.is_empty, 0, device=entity, room=room)
            return
        elif any(humidifier_penalties.values()) and room == 'bedroom':
            self.log_info(
                message=f"""
                    In set_humidifier_mode - {room}:
                    The priority device is humidifier.
                    Encountered penalties for the humidifier.
                    {humidifier_penalties}
                    Setting Baby Mode for the Humidifier
                    """,
                level='INFO',
                log_room=room,
                function_name='set_humidifier_mode'
            )
            self.call_service("humidifier/set_mode", entity_id=list(humidifier_entities.keys()), mode='baby')
            for entity in humidifier_entities:
                self.run_in(self.is_empty, 0, device=entity, room=room)

            return

        else:
            self.call_service("humidifier/set_mode", entity_id=list(humidifier_entities.keys()), mode='manual')
            return True

    def set_diffuser_mode(self, room):
        return True

    def check_warnings(self, room, sensor_data):

        warning_thresholds = {}
        # Get UI Warning Thresholds
        for sensor, thresholds in self.warning_thresholds.items():
            ui_thresholds = {}
            for threshold, value in thresholds.items():
                try:
                    ui_sensor = f'input_number.warning_thresholds_{sensor}_{threshold}'
                    ui_thresholds[threshold] = float(self.get_state(ui_sensor))
                except Exception as e:
                    self.log_info(
                        message=f"""
                            In check_warnings - {room}:
                            Error: {e}
                            Sensor: {sensor}
                            Threshold: {threshold}
                        """,
                        level='INFO',
                        log_room=room,
                        function_name='check_warnings'
                    )
                    ui_thresholds[threshold] = value
            warning_thresholds[sensor] = ui_thresholds

        # Check Current Sensor Data for Warnings
        warnings = {}
        for sensor, value in sensor_data.items():
            if sensor not in warning_thresholds:
                continue
            warn_dict = {'high': '', 'low': '', 'msg': ''}
            warnings[sensor] = warn_dict
            for threshold, threshold_value in warning_thresholds[sensor].items():
                if float(value) >= threshold_value and threshold == 'high':
                    warning = f"{sensor.title()} is above {threshold} threshold of {threshold_value}."
                    warn_bool = True
                    self.log_info(
                        message=f"""
                            In Air Quality check_warnings - {room}:
                            {warning}
                            
                            Current {sensor.title()}: {value}
                        """,
                        level='INFO',
                        log_room=room,
                        function_name='check_warnings',
                        # notify_device='everyone',
                    )

                elif float(value) < threshold_value and threshold == 'low':
                    warning = f"{sensor.title()} is below {threshold} threshold of {threshold_value}."
                    warn_bool = True
                    self.log_info(
                        message=f"""
                            In Air Quality check_warnings - {room}:
                            {warning}
                            
                            Current {sensor.title()}: {value}
                        """,
                        level='INFO',
                        log_room=room,
                        function_name='check_warnings',
                        # notify_device='everyone',
                    )
                else:
                    warning = 'OK'
                    warn_bool = False

                warnings[sensor][threshold] = warn_bool
                warnings[sensor]['msg'] = warning

        return warnings

    def update_air_quality_entities_for_room(self, room, priority_device, sensor_data, time_scores, weight_score):
        """Update the Air Quality entities in Home Assistant for a specific room."""
        self.log_info(
            message=f"""
                Entering update_air_quality_entities_for_room - {room}
                The priority device is {priority_device}
                Sensor Data:
                    {', '.join([f"{metric.upper()}: {sensor_data.get(metric, 'N/A')}" for metric in sensor_data])}
            """,
            level='DEBUG',
            log_room=room,
            function_name='update_air_quality_entities_for_room'
        )

        # Prepare the viewable string for time scores
        viewable_string = ''
        for device, score in time_scores.items():
            viewable_string += f"{device}: {score:.2f}\t"

        # Update input_text entities for priority device and sensor data
        self.set_state(f"input_text.{room}_air_quality_priority_device", state=priority_device)

        # Set sensor data states
        for metric, value in sensor_data.items():
            if isinstance(value, (int, float)):
                self.set_state(f"input_text.{room}_air_quality_{metric}", state=f"{value}")
                self.set_state(f"input_number.{room}_air_quality_{metric}", state=f"{value:.2f}")

        # Update time and weight scores
        self.set_state(f"input_text.{room}_air_quality_time_score", state=viewable_string)
        self.set_state(f"input_text.{room}_air_quality_weight_score", state=f"{weight_score:.2f}")

        # Update priority scores for each device
        for device in ['purifier', 'humidifier', 'fan', 'oil_diffuser']:
            device_score = time_scores.get(device, 0)
            self.set_state(
                f"input_number.{room}_air_quality_{device}_score",
                state=f"{device_score:.2f}"
            )

    def generate_logging_cards(self, **kwargs):
        """Generates cards representing all occupancy binary sensors in the home"""

        def add_glance_card(title, entities):
            """Creates a Home Assistant 'glance' card with the given title and list of entities"""
            return {
                "type": "glance",
                "title": title,
                "entities": entities,
                "show_name": True,
                "show_icon": True,
                "show_state": True
            }

        def add_entities_card(title, entities):
            """Creates a Home Assistant 'entities' card with the given title and list of entities"""
            return {
                "type": "entities",
                "title": title,
                "entities": entities,
            }

        def add_markdown_card(content):
            """Creates a Home Assistant 'markdown' card with the given content"""
            return {
                "type": "markdown",
                "content": content
            }

        def add_vertical_stack_card(cards):
            """Creates a Home Assistant 'vertical-stack' card with the given list of cards"""
            return {
                "type": "vertical-stack",
                "cards": cards
            }

        def add_state_switch_card(states):
            return {
                "type": "custom:state-switch",
                "entity": f'input_select.{self.app_name_short}_device_type',
                "states": states
            }

        def add_apexcharts_card(title, entity_id, series_name):
            """Creates a 'custom:apexcharts-card' for visualizing sensor data"""
            return {
                "type": "custom:apexcharts-card",
                "header": {
                    "show": True,
                    "title": title,
                },
                "graph_span": "24h",
                "span": {
                    "start": "day",
                },
                "now": {
                    "show": True,
                    "label": "Now",
                },
                "series": [
                    {
                        "entity": entity_id,
                        "name": series_name,
                        "type": "line",
                        # Customize additional series options as needed
                    }
                ],
                # Add any additional customization here
            }

        on_booleans = {
            "master_and_user_overrides": None,
            "is_room_occupied": None,
            "is_anyone_home": None,
            "humidifier": None,
            "purifier": None,
            "oil_diffuser": None,
            "fan": None,
            "priority_device": None,
            "warnings": None,
            "air_circulation": None,
            "deodorize_and_refresh": None,
            "humidify": None,
            'latency': None,
            'last_triggered': None,
        }
        off_booleans = {
            "master_and_user_overrides": None,
            "is_room_not_occupied": None,
            'latency': None,
            'last_triggered': None,
        }
        cards = []

        glance_entities = {}
        room_automation_boolean_checks = {}
        room_details = {}
        for log_sensor, room in self.room_automation_booleans.items():
            log_sensor_str = log_sensor.replace(" ", "_").lower()
            if room not in room_automation_boolean_checks:
                room_automation_boolean_checks[room] = {}
                room_details[room] = {
                    'master_on': {
                        'attributes_cache': {device_type: {} for device_type in self.device_types},
                        'entity_details': {device_type: [] for device_type in self.device_types}
                    },
                    'master_off': {
                        'attributes_cache': {device_type: {} for device_type in self.device_types},
                        'entity_details': {device_type: [] for device_type in self.device_types}
                    }
                }

            if 'on_conditions' in log_sensor_str:
                attributes_cache = room_details[room]['master_on']['attributes_cache']
                entity_details = room_details[room]['master_on']['entity_details']

                for device_type in self.device_types:
                    if device_type in log_sensor_str:
                        for attr in on_booleans:
                            if attr not in attributes_cache[device_type]:
                                attributes_cache[device_type][attr] = True
                            else:
                                continue
                            entity_details[device_type].append({
                                "type": "attribute",
                                "entity": f'{log_sensor.replace(" ", "_").lower()}',
                                "name": f"{attr.replace('_', ' ').title()}",
                                "attribute": attr,
                                "icon": "mdi:account"  # Customize the icon as needed
                            })

                        entity_details[device_type].append({
                            "entity": f'{log_sensor.replace(" ", "_").lower()}',
                            "name": "Current Status",
                        })

                room_automation_boolean_checks[room]['master_on'] = {'log_sensor': log_sensor,
                                                                     'entity_details': entity_details}
            elif 'off_conditions' in log_sensor_str:
                attributes_cache = room_details[room]['master_off']['attributes_cache']
                entity_details = room_details[room]['master_off']['entity_details']

                for device_type in self.device_types:
                    if device_type in log_sensor_str:
                        for attr in off_booleans:
                            if attr not in attributes_cache:
                                attributes_cache[device_type][attr] = True
                            else:
                                continue
                            entity_details[device_type].append({
                                "type": "attribute",
                                "entity": f'{log_sensor.replace(" ", "_").lower()}',
                                "name": f"{attr.replace('_', ' ').title()}",
                                "attribute": attr,
                                "icon": "mdi:account"  # Customize the icon as needed
                            })
                        entity_details[device_type].append({
                            "entity": f'{log_sensor.replace(" ", "_").lower()}',
                            "name": "Current Status",
                        })
                room_automation_boolean_checks[room]['master_off'] = {'log_sensor': log_sensor,
                                                                      'entity_details': entity_details}

        for room, room_details in room_automation_boolean_checks.items():
            state_cards = {}
            for device_type in self.device_types:
                state_cards.update(
                    {
                        device_type: add_vertical_stack_card(
                            [
                                add_entities_card(
                                    f"{room.replace('_', ' ').title()} - {device_type.replace('_', ' ').title()} Master On",
                                    room_details['master_on']['entity_details'][device_type]
                                ),
                                add_entities_card(
                                    f"{room.replace('_', ' ').title()} - {device_type.replace('_', ' ').title()} Master Off",
                                    room_details['master_off']['entity_details'][device_type]
                                ),
                            ]
                        )
                    }
                )
            cards.append(add_state_switch_card(state_cards))

        # --- New code to add organized charts for aggregated sensors ---
        # Define sensor types and their categories
        sensor_categories = {
            'Particulate Matter': ['pm2_5', 'pm10', 'pm1', 'pm4'],
            'Gases': ['nox', 'co2', 'voc', 'methane', 'carbon_monoxide', 'nitrogen_dioxide', 'ethanol', 'hydrogen',
                      'ammonia'],
            'Environmental Factors': ['temperature', 'humidity', 'air_pressure'],
        }

        rooms = set(self.room_automation_booleans.values())

        for room in rooms:
            room_name_formatted = room.replace('_', ' ').title()
            category_cards = []

            for category_name, sensor_types in sensor_categories.items():
                sensor_cards = []
                for sensor_type in sensor_types:
                    if sensor_type.endswith('y'):
                        sensor_type = sensor_type[:-1] + 'ies'
                        entity_id = f'sensor.{room}_{sensor_type}'
                    else:
                        entity_id = f'sensor.{room}_{sensor_type}s'

                    if self.get_state(entity_id):
                        chart_title = f"{sensor_type.upper()} Levels"
                        chart_card = add_apexcharts_card(chart_title, entity_id, sensor_type.upper())
                        sensor_cards.append(chart_card)

                if sensor_cards:
                    # Group sensor charts in a vertical stack within the category
                    category_stack = add_vertical_stack_card(sensor_cards)
                    # Add a markdown card for the category title
                    category_title_card = {
                        "type": "markdown",
                        "content": f"## {category_name}"
                    }
                    # Combine title and charts
                    category_cards.append(add_vertical_stack_card([category_title_card, category_stack]))

            if category_cards:
                # Add a markdown card for the room title
                room_title_card = {
                    "type": "markdown",
                    "content": f"# {room_name_formatted}"
                }
                # Group all category cards for the room
                room_stack = add_vertical_stack_card([room_title_card] + category_cards)
                cards.append(room_stack)
        # --- End of new code ---

        self.call_service(
            service='pyscript/receive_custom_dashboard_cards',
            app_name=self.app_name_short,
            cards=cards,
            custom_card_id='windows_automation_boolean_checks'
        )
