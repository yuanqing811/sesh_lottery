import re
import argparse
from datetime import datetime
from event import EventType
from sesh import START_DATE, cancelled_event_name_regex, EVENT_NAME


def convert_date_str_to_obj(date_str):
	# Convert to datetime object
	event_date_regex = "%Y-%m-%d"  # ex. ""2023-10-08" or "2024-10-22"

	date_obj = datetime.strptime(date_str, event_date_regex).date()
	return date_obj


def classify_event(event_name):
	if re.search(r'clinic', event_name, re.IGNORECASE):
		return EventType.CLINIC
	if re.search(r'round robin', event_name, re.IGNORECASE):
		return EventType.ROUNDROBIN
	return EventType.OTHER


def determine_event_dupr_range(event_name):
	# TODO: check for dupr range ex. "3.5-4.0",
	# "3.0 to 3.5", "4.5+", or "2.5, 3.0, 3.25",
	# "all levels"
	raise NotImplementedError


def clean_clinic_name(event_name):
	# TODO: currently filtering by event name exactly is too brittle, not allowing for typos or slight variations
	return event_name


def remove_canceled_event(cancelled_clinic_set_df, clinic_set_df):
	conditions = []
	for idx, cancelled_clinic_row in cancelled_clinic_set_df.iterrows():
		start_date = cancelled_clinic_row[START_DATE]
		clinic_name = re.findall(
			cancelled_event_name_regex,
			cancelled_clinic_row[EVENT_NAME],
			flags=re.IGNORECASE)[0]
		conditions.append((
				(clinic_set_df[START_DATE] == start_date) &
				(clinic_set_df[EVENT_NAME] == clean_clinic_name(clinic_name))  # TODO:not good enough
		))
	combined_condition = conditions[0]
	for condition in conditions[1:]:
		# OR (|) logic to combine conditions
		combined_condition |= condition
	# Remove rows that match any of the combined conditions
	clinic_set_df = clinic_set_df[~combined_condition]
	return clinic_set_df


if __name__ == "__main__":
	# create argument parser
	parser = argparse.ArgumentParser(description="Run a sesh_util function for testing")

	# Positional argument for function name
	parser.add_argument("function_name", help="Name of the function to run")

	# Positional arguments for function parameters (as strings, will convert later)
	parser.add_argument("args", nargs="*", help="Arguments to pass to the function")

	# Parse arguments
	args = parser.parse_args()

	# Get the function by name (make sure the function exists in globals)
	func = globals().get(args.function_name)

	if func is None:
		print(f"Function '{args.function_name}' not found.")
	else:
		# Call the function with the provided arguments
		result = func(*args.args)

		print(f"Result of {args.function_name}: {result}")
