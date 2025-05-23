import datetime
import argparse
import os
import sys

import yaml


# This custom class forces inline (flow style) for specific values
class InlineList(list):
    pass


def represent_inline_list(dumper, data):
    return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True)


yaml.add_representer(InlineList, represent_inline_list)


from sesh import SeshData, START_DATE, RSVPER_NAMES, EVENT_TYPE, LOTTERY, ATTENDEES, RSVPER_LINK
from sesh_util import extract_server_and_event_id
from lottery import Lottery
from history import EventParticipationTracker
from sesh_util import convert_date_str_to_obj
from logging_config import configure_logging
from whosin import coach_huddle_whosin
from sesh_dashboard.event import SeshDashboardEvent


class ClinicLottery:
    def __init__(self, config: dict):
        self.csv_filename = config['csv_filename']
        self.output_dir = config['output_dir']
        self.start_date = config['start_date']
        self.recurring_interval_in_days = config['recurring_interval_in_days']
        self.event_configs = config['events']
        self.exclude_from_lottery = config['exclude_from_lottery']

        # track participants across clinic lotteries
        self.all_rsvper_names = []

        self.sesh_data = SeshData(self.csv_filename)
        self.clinic_events = self.sesh_data.get_clinic_events()

        # todo: remove_cancelled_event has to take an additional argument,
        # which is a link to a google sheet which keeps track of all the cancelled events
        self.clinic_events = self.sesh_data.remove_canceled_event(self.clinic_events)

        # self.clinic_events[RSVPER_NAMES] = self.clinic_events[RSVPER_NAMES, ATTENDEES]
        clinic_attendance_tracker = EventParticipationTracker(self.clinic_events)

        self.lottery_events = self.get_lottery_events(
            start_date=self.start_date,
            recurring_interval_in_days=self.recurring_interval_in_days
        )

        output_filename = self.get_output_filename()
        if os.path.exists(output_filename):
            os.remove(output_filename)

        whosin_filename = f'{self.output_dir}/whosin.txt'
        if os.path.exists(whosin_filename):
            os.remove(whosin_filename)

        sesh_dashboard_data_filename = f'{self.output_dir}/Clinic_sesh_dashboard_data.yaml'
        if os.path.exists(sesh_dashboard_data_filename):
            os.remove(sesh_dashboard_data_filename)

        for idx, lottery_event in self.lottery_events.iterrows():
            event_type = lottery_event[EVENT_TYPE]
            event_date = lottery_event[START_DATE]
            rsvper_link = lottery_event[RSVPER_LINK]
            server_id, event_id = extract_server_and_event_id(rsvper_link)
            print(f'server ID: {server_id}, event ID: {event_id}')
            print(lottery_event)
            # get rsvper names -- people who have entered lottery
            rsvper_names = lottery_event[RSVPER_NAMES, LOTTERY]
            print(f'rsvper_names: {rsvper_names}')

            # todo: sometimes users enter their names in the attendee list by mistake
            other_rsvper_names = lottery_event[RSVPER_NAMES, ATTENDEES]

            if len(other_rsvper_names) > 0:
                print(f'other_rsvper_names: {other_rsvper_names}')
                rsvper_names.extend(other_rsvper_names)

            max_num_attendees = lottery_event['max_attendee_count']
            num_past_sessions = lottery_event['num_past_sessions']

            latest_events = self.sesh_data.get_latest_events(
                before_event_date=lottery_event[START_DATE],
                event_type=lottery_event[EVENT_TYPE],
                max_sessions=num_past_sessions)
            latest_dates = latest_events[START_DATE].to_list()

            clinic_attendance_df = clinic_attendance_tracker.get_history(
                attendee_names=rsvper_names,
                dates=latest_dates
            )
            lottery = Lottery(
                event_type=event_type,
                attendance_df=clinic_attendance_df,
                max_num_attendees=max_num_attendees
            )
            lottery.select_and_sort_attendees(
                exclude_from_lottery=self.exclude_from_lottery,
                all_participants=self.all_rsvper_names)

            attendee_names = lottery.participant_df[Lottery.PTCPNT_COL_NAME].tolist()
            print('attendee names:', attendee_names)

            self.track_rsvpers(rsvper_names)

            table_name = f'{event_type}_{event_date}'
            self.write_table_to_csv(
                lottery=lottery,
                table_name=table_name,
                csv_filename=output_filename,
            )

            self.write_event_data_to_file(
                server_id=server_id,
                event_id=event_id,
                lottery_list=other_rsvper_names,
                attendee_list=attendee_names,
                filename=sesh_dashboard_data_filename
            )

        coach_huddle_whosin(self.lottery_events, write_to_csv=whosin_filename)

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
        # lottery_events[RSVPER_NAMES] = lottery_events[RSVPER_NAMES, LOTTERY]
        lottery_events = lottery_events.dropna(subset=[RSVPER_NAMES])

        # sort clinic_config based on lottery order
        lottery_events.sort_values(by='lottery_order', ascending=True, inplace=True)
        return lottery_events

    def get_output_filename(self):
        print(self.lottery_events)
        first_event_date = self.lottery_events.iloc[0][START_DATE]
        output_filename = f'{self.output_dir}/Clinics_{first_event_date}.csv'
        return output_filename

    @staticmethod
    def merge_flags(lottery):
        # Join the sub-columns with a comma
        merged_flags_col = []

        for idx, row in lottery.participant_df.iterrows():
            new_flag = []
            level_switch_flag = row[(lottery.FLAGS_COL_NAME, 'level_switch')]
            multi_signup_flag = row[(lottery.FLAGS_COL_NAME, 'multi_signup')]
            if level_switch_flag and len(level_switch_flag) > 0:
                new_flag.append(row[(lottery.FLAGS_COL_NAME, 'level_switch')])
            if multi_signup_flag is True:
                new_flag.append('multi')
            merged_flags = ','.join(new_flag)
            merged_flags_col.append(merged_flags)
        return merged_flags_col

    def track_rsvpers(self, rsvper_names):
        for name in rsvper_names:
            if name not in self.all_rsvper_names:
                self.all_rsvper_names.append(name)

    def write_table_to_csv(self, lottery, table_name, csv_filename):

        # self.logger.info("Writing the lottery participants' statistics to a csv file")
        output_columns = [
            (lottery.PTCPNT_COL_NAME, ''),
            (lottery.PRIORITY_COL_NAME, lottery.SCORE_COL_NAME)
        ]

        # Check which of them exist in the DataFrame
        attendance_columns = [
            col for col in lottery.participant_df.columns
            if isinstance(col, tuple) and col[0] == lottery.ATTENDANCE_COL_NAME
        ]

        output_columns = output_columns + attendance_columns

        output_df = lottery.participant_df[output_columns].copy()
        flags_col = self.merge_flags(lottery)

        flags_col_name = ('Flags', '')
        output_df[flags_col_name] = flags_col
        insert_after_col_name = (lottery.PTCPNT_COL_NAME, '')
        insert_after = output_columns.index(insert_after_col_name)
        insert_at = insert_after + 1

        output_columns.insert(insert_at, flags_col_name)

        with open(csv_filename, "a") as file:
            file.write(f"\n{table_name}\n")

        output_df[output_columns].to_csv(
            csv_filename, mode='a', header=True, index=True
        )
        file.close()

    def write_event_data_to_file(self, server_id, event_id, lottery_list, attendee_list, filename):
        with open(filename, "a") as f:
            yaml.dump(
                {
                    'server_id': server_id,
                    'event_id': event_id,
                    'add_to_lottery': InlineList(lottery_list),
                    'add_to_attendee': InlineList(attendee_list),
                }, f, sort_keys=False)
            f.write('---\n')  # optional but recommended to separate documents

    def upload_attendees_to_sesh_dashboard(self, server_id, event_id, lottery_list, attendee_list):
        sesh_event_add_attendees = SeshDashboardEvent(server_id=server_id)
        sesh_event_add_attendees.add_attendees_to_event(event_id=event_id,
                                                        attendees=attendee_list)


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
        days_until_monday = (7 - today.weekday()) % 7  # 0 for Monday, 1 for Tuesday, etc.
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

    #todo:download the csv
    clinic_Lottery = ClinicLottery(config)
