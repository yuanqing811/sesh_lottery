import argparse
from datetime import datetime


def convert_date_str_to_obj(date_str):
	# Convert to datetime object
	event_date_regex = "%Y-%m-%d"  # ex. ""2023-10-08" or "2024-10-22"

	date_obj = datetime.strptime(date_str, event_date_regex).date()
	return date_obj

