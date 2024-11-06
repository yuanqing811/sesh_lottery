import re
import datetime
from enum import Enum
from sesh import EVENT_NAME, EVENT_TYPE, START_DATE, RSVPER_NAMES
from sesh import EventType
from sesh_util import convert_date_str_to_obj


class ClinicEventManager:
	def __init__(self, df):
		self.df = df
		self.df = self.df[self.df[EVENT_TYPE].str.contains('Clinic', case=False, na=False)]
		self.df = self.df[[EVENT_NAME, EVENT_TYPE, START_DATE, RSVPER_NAMES]]

	def get_event(self, event_type, event_date):
		df = self.df[(self.df[START_DATE] == event_date) & (self.df[EVENT_TYPE] == event_type)]
		return df.head(1)

	def get_latest_events(self, event_type, event_date=None, max_sessions=3):
		if event_date is None:
			event_date = datetime.date.today()
		elif isinstance(event_date, str):
			event_date = convert_date_str_to_obj(event_date)
		elif not isinstance(event_date, datetime.date):
			raise TypeError(f'event_date {event_date} needs to be of type(datetime.date)')

		df = self.df[(self.df[START_DATE] < event_date) & (self.df[EVENT_TYPE] == event_type)]
		df = df.sort_values(
			by=START_DATE,
			ascending=False
		)

		# Get the date of the first and last sessions within the first max_sessions rows
		df = df.head(max_sessions)
		last_session_date = df.head(1)[START_DATE].iloc[0]
		first_session_date = df.tail(1)[START_DATE].iloc[0]

		df = df[
			(df[START_DATE] >= first_session_date) &
			(df[START_DATE] <= last_session_date)
		]
		return df

