import datetime
import argparse
import os
import sys
import yaml

from sesh import SeshData, START_DATE, RSVPER_NAMES, EVENT_TYPE, ATTENDEES, LOTTERY
from lottery import Lottery
from history import EventParticipationTracker
from sesh_util import convert_date_str_to_obj
from logging_config import configure_logging


class RecurringClinicLottery:
    def __init__(self, config: dict):
        self.csv_filename = config['csv_filename']
        self.output_dir = config['output_dir']
        self.start_date = config['start_date']
        self.recurring_interval_in_days = config['recurring_interval_in_days']
        self.event_configs = config['events']

        # track participants across clinic lotteries
        self.lottery_participants = []

        self.sesh_data = SeshData(self.csv_filename)
        self.clinic_events = self.sesh_data.get_clinic_events()
        self.clinic_events = self.sesh_data.remove_canceled_event(self.clinic_events)
        self.clinic_events[RSVPER_NAMES] = self.clinic_events[RSVPER_NAMES, ATTENDEES]
        clinic_attendance_tracker = EventParticipationTracker(self.clinic_events)

        lottery_events = self.get_lottery_events(
            start_date=self.start_date,
            recurring_interval_in_days=self.recurring_interval_in_days
        )

        for idx, lottery_event in lottery_events.iterrows():
            event_type = lottery_event[EVENT_TYPE]
            event_date = lottery_event[START_DATE]
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
            lottery = Lottery(event_type=event_type,
                              attendance_df=sm_df,
                              low_priority_participants=self.lottery_participants)

            lottery.select_attendees_and_waitlist(num_participants=max_attendees,
                                                  write_to_csv=f'{self.output_dir}/{event_type}_{event_date}.csv')

    def get_lottery_events(self,
                           start_date: datetime.date,
                           recurring_interval_in_days: datetime.timedelta):

        end_date = start_date + recurring_interval_in_days

        lottery_events = self.clinic_events[
            (self.clinic_events[START_DATE] >= start_date) &
            (self.clinic_events[START_DATE] < end_date)
            ].copy()

        lottery_order = []
        max_attendee_count = []
        num_past_sessions = []
        for idx, event in lottery_events.iterrows():
            event_type = event[EVENT_TYPE]
            event_config = self.event_configs[event_type]
            lottery_order.append(event_config['lottery']['order'])
            max_attendee_count.append(event_config['lottery']['max_attendee_count'])
            num_past_sessions.append(event_config['attendance_history']['num_past_sessions'])

        lottery_events['lottery_order'] = lottery_order
        lottery_events['num_past_sessions'] = num_past_sessions
        lottery_events['max_attendee_count'] = max_attendee_count
        lottery_events[RSVPER_NAMES] = lottery_events[RSVPER_NAMES, LOTTERY]
        lottery_events = lottery_events.dropna(subset=[RSVPER_NAMES])

        # sort clinic_config based on lottery order
        lottery_events.sort_values(by='lottery_order', ascending=True, inplace=True)
        return lottery_events


def process_yaml_file(yaml_filename):
    # Process the file
    if not os.path.exists(yaml_filename):
        print(f"Error: The file '{yaml_filename}' does not exist.")
        sys.exit(1)

    try:
        with open(yaml_filename, 'r') as file:
            clinic_lottery_configs = yaml.safe_load(file)
    except Exception as e:
        raise Exception(f"Error processing the file: {e}")

    try:
        start_date = clinic_lottery_configs['start_date']
    except KeyError:
        raise Exception("Error retrieving start_date from yaml file")

    if not (start_date is None):
        if isinstance(start_date, str):
            start_date = convert_date_str_to_obj(start_date)
        elif not isinstance(start_date, datetime.date):
            raise Exception(f'wrong data type for {start_date}')
    else:		# start_date is None, meaning get next Monday
        # Get today's date
        today = datetime.datetime.now()

        # Calculate the number of days until the next Monday
        days_until_monday = (7 - today.weekday())% 7  # 0 for Monday, 1 for Tuesday, etc.
        days_until_monday = days_until_monday if days_until_monday != 0 else 7

        # Calculate the next Monday's date
        start_date = today + datetime.timedelta(days=days_until_monday)
    clinic_lottery_configs['start_date'] = start_date

    try:
        recurring_interval_in_days = clinic_lottery_configs['recurring_interval_in_days']
    except KeyError:
        raise Exception("Error retrieving recurring_interval_in_days from yaml file")
    if recurring_interval_in_days is None:
        recurring_interval_in_days = 7
    if not isinstance(recurring_interval_in_days, int):
        raise Exception(f'wrong data type for recurring_interval_in_days, should be int')
    recurring_interval_in_days = datetime.timedelta(recurring_interval_in_days)
    clinic_lottery_configs['recurring_interval_in_days'] = recurring_interval_in_days
    return clinic_lottery_configs


if __name__ == "__main__":
    configure_logging()

    # Set up argument parser
    parser = argparse.ArgumentParser(description="Process a file provided as a command-line argument.")
    parser.add_argument('filename', type=str, help='The path to the file to be processed')

    # Parse the arguments
    args = parser.parse_args()
    config = process_yaml_file(args.filename)
    clinic_Lottery = RecurringClinicLottery(config)


