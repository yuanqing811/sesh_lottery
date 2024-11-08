from sesh import SeshData, START_DATE, RSVPER_NAMES, LOTTERY
from lottery import Lottery
from sesh_util import convert_date_str_to_obj
from history import AttendanceHistory
import pandas as pd
import datetime


if __name__ == '__main__':
	import yaml

	# Load data from the YAML file
	with open('clinic.yaml', 'r') as file:
		clinic_configs = yaml.safe_load(file)

	sesh_data = SeshData(clinic_configs['csv_filename'])
	output_dir = clinic_configs['output_filedir']

	# Print each entry
	for event_lottery_config in clinic_configs['events']:
		# get the configuration for running lottery
		event_type = event_lottery_config['event']['type']
		event_date = event_lottery_config['event']['date']
		if not (event_date is None):
			if isinstance(event_date, str):
				event_date = convert_date_str_to_obj(event_date)
			elif not isinstance(event_date, datetime.date):
				raise Exception(f'wrong data type for {event_date}')
		max_attendees = event_lottery_config['attendees']['max_count']
		attendees_to_exclude = event_lottery_config['attendees']['exclude_from_lottery']
		num_past_sessions = event_lottery_config['attendance_history']['num_past_sessions']

		try:
			event = sesh_data.get_event(event_type=event_type, event_date=event_date)
		except:
			print(f'cannot find event {event_type} on date {event_date}, could it have been cancelled?')
			continue

		names = event[RSVPER_NAMES][LOTTERY]
		events = sesh_data.get_latest_events(
			before_event_date=event_date,
			event_type=event_type,
			max_sessions=num_past_sessions)
		latest_dates = events[START_DATE].to_list()
		clinic_events = sesh_data.get_clinic_events()
		attendance_history = AttendanceHistory(latest_dates, clinic_events)
		sm_df = attendance_history.get_df_for_attendees(names)
		lottery = Lottery(attendance_df=sm_df)
		lottery.compute_priority()
		lottery.select_winners(num_winners=max_attendees)
		with pd.option_context('display.max_columns', None):
			print(lottery.attendee_stats_df)

		# Write DataFrame to a CSV file
		# Write dictionary to a YAML file
		with open(f'{output_dir}/{event_type}_{event_date}.yaml', 'w') as f:
			yaml.dump(lottery.result, f)
		lottery.attendee_stats_df.to_csv(f'{output_dir}/{event_type}_{event_date}_output.csv', index=True)

