from sesh import SeshData, START_DATE, RSVPER_NAMES, EVENT_TYPE, ATTENDEES, LOTTERY
from lottery import Lottery
from sesh_util import convert_date_str_to_obj
from history import EventParticipationTracker
import datetime
import pandas as pd
import yaml


class WeeklyClinicLottery:
    def __init__(self, config_yaml_filename):
        # Load data from the YAML file
        with open(config_yaml_filename, 'r') as file:
            self.clinic_lottery_configs = yaml.safe_load(file)

        # sort clinic_config based on lottery order
        self.clinic_lottery_configs['events'].sort(key=lambda x: x['lottery']['order'])
        output_dir = self.clinic_lottery_configs['output_filedir']
        self.lowprio_attendees = []

        self.sesh_data = SeshData(self.clinic_lottery_configs['csv_filename'])
        self.clinic_events = self.sesh_data.get_clinic_events()
        self.clinic_events[RSVPER_NAMES] = self.clinic_events[RSVPER_NAMES, ATTENDEES]
        clinic_attendance_tracker = EventParticipationTracker(self.clinic_events)

        lottery_events = self.get_lottery_events()
        lottery_events[RSVPER_NAMES] = lottery_events[RSVPER_NAMES, LOTTERY]

        for idx, lottery_event in lottery_events.iterrows():
            names = lottery_event[RSVPER_NAMES]  # get names of people who have entered lottery
            max_attendees = lottery_event['max_attendee_count']
            num_past_sessions = lottery_event['num_past_sessions']

            latest_events = self.sesh_data.get_latest_events(
                before_event_date=lottery_event[START_DATE],
                event_type=lottery_event[EVENT_TYPE],
                max_sessions=num_past_sessions)
            latest_dates = latest_events[START_DATE].to_list()

            sm_df = clinic_attendance_tracker.get_history(
                attendee_names=names, dates=latest_dates)

            lottery = Lottery(attendance_df=sm_df)
            lottery.compute_priority()

            for attendee in names:
                if attendee in self.lowprio_attendees:
                    # lower the priority of attendees who should be excluded
                    lottery.set_priority(attendee, 100)

            lottery.select_winners(num_winners=max_attendees)

        lottery_entry_tracker = EventParticipationTracker(lottery_events)
        lottery_entry_tracker.get_history(lottery_events[START_DATE].tolist(), self.lowprio_attendees)
        lottery_flag_df = lottery_entry_tracker.check_for_level_switching()
        clinic_flag_df = clinic_attendance_tracker.check_for_level_switching()

        flag_dfs = pd.concat([lottery_flag_df, clinic_flag_df], axis=1, join="outer")
        new_columns = ['lottery multiple signups', 'clinic level switching']
        flag_dfs = flag_dfs.set_axis(new_columns, axis=1)
        # Drop rows where all values are None
        flag_dfs = flag_dfs.dropna(how='all')
        flag_dfs.to_csv(f'{output_dir}/clinic_lottery_output.csv', index=True)

    def get_lottery_events(self):
        lottery_events = []
        lottery_event_configs = []
        num_past_sessions_list = []
        max_attendee_count_list = []

        for event_lottery_config in self.clinic_lottery_configs['events']:
            # get the configuration for running lottery
            event_type = event_lottery_config['event']['type']
            event_date = event_lottery_config['event']['date']
            num_past_sessions = event_lottery_config['attendance_history']['num_past_sessions']
            max_attendee_count = event_lottery_config['lottery']['max_attendee_count']

            if not (event_date is None):
                if isinstance(event_date, str):
                    event_date = convert_date_str_to_obj(event_date)
                elif not isinstance(event_date, datetime.date):
                    raise Exception(f'wrong data type for {event_date}')

            try:
                event = self.sesh_data.get_event(event_type=event_type, event_date=event_date)
            except:
                print(f'cannot find event {event_type} on date {event_date}, could it have been cancelled?')
                continue
            lottery_events.append(event)
            lottery_event_configs.append(event_lottery_config)
            num_past_sessions_list.append(num_past_sessions)
            max_attendee_count_list.append(max_attendee_count)

        lottery_events_df = pd.concat(lottery_events, axis=1, ignore_index=True).T
        lottery_events_df[RSVPER_NAMES] = lottery_events_df[RSVPER_NAMES, LOTTERY]
        lottery_events_df['max_attendee_count'] = max_attendee_count_list
        lottery_events_df['num_past_sessions'] = num_past_sessions_list
        return lottery_events_df
