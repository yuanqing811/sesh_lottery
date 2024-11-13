import datetime
import pandas as pd
from sesh import START_DATE, RSVPER_NAMES, EVENT_TYPE
from sesh_util import ADV_BEG_CLINIC, ADV_INT_CLINIC, BEG_CLINIC, INT_CLINIC


class EventParticipationTracker:
	PARTICIPANT = 'Participant'
	HISTORY = 'History'

	def __init__(self, events_df) -> None:
		"""
		Initialize the EventEntryTracker with a DataFrame of events.

		:param events_df: 	DataFrame with 'event_name' (name of event), 'start_date' column (date)
							and 'Attendees' column (list of attendee names).
		"""
		self.events_df = events_df.copy()
		self.df = None
		self.flags = None

	@staticmethod
	def _get_week_date_range(event_date):
		"""
		Get the start and end dates of the week (Monday to Sunday) for a given date.

		:param event_date: The specific date to find the week range for.
		:return: date_range(start=start_of_week, periods=7)
		"""
		# Calculate the start of the week (Monday)
		start_of_week = event_date - datetime.timedelta(days=event_date.weekday())
		week_range = pd.date_range(start=start_of_week, periods=7)
		return week_range

	def _generate_history_for_date_range(self, date_range):
		# Initialize an empty dictionary to hold attendance records for each attendee
		attendance_data = {}

		date_range_label = f"{date_range[0].date()} to {date_range[-1].date()}"

		events_in_date_range = self.events_df[
			(self.events_df[START_DATE] >= date_range[0].date()) &
			(self.events_df[START_DATE] <= date_range[-1].date())
			]

		for idx, event in events_in_date_range.iterrows():
			attendees_in_event = event[RSVPER_NAMES]
			# Update the attendance data dictionary
			for attendee in attendees_in_event:
				if attendee not in attendance_data:
					attendance_data[attendee] = {}
				if date_range_label not in attendance_data[attendee]:
					attendance_data[attendee][date_range_label] = []
				attendance_data[attendee][date_range_label].append(event[EVENT_TYPE])

		# Convert the attendance data dictionary to a DataFrame
		df = pd.DataFrame.from_dict(attendance_data, orient='index')

		# Reset index to add attendee names as a column
		df.reset_index(inplace=True)
		df.rename(columns={'index': self.PARTICIPANT}, inplace=True)
		df.set_index(self.PARTICIPANT, inplace=True)
		return df

	def _generate_history(self, dates):
		"""
		Generate the history DataFrame with attendees as rows and weekly attendance as columns.

		:return: DataFrame where rows are attendees, columns are weekly attendance (True/False).
		"""

		dates = sorted(dates, reverse=True)
		date_ranges = []
		date_range_labels = []

		for event_date in dates:
			date_range = self._get_week_date_range(event_date)
			date_range_label = f"{date_range[0].date()} to {date_range[-1].date()}"

			if date_range_label in date_range_labels:
				continue

			date_ranges.append(date_range)
			date_range_labels.append(date_range_label)

		dfs = []

		for date_range in date_ranges:
			# Determine the week date range as a Pandas date range
			week_range_df = self._generate_history_for_date_range(date_range)
			dfs.append(week_range_df)

		attendance_df = pd.concat(dfs, axis=1, join="outer")
		attendance_df.columns = pd.MultiIndex.from_product([[self.HISTORY], attendance_df.columns])
		return attendance_df

	@staticmethod
	def count_unique_non_nan(row):
		flattened_values = pd.Series(
			[item for cell in row.dropna() for item in (cell if isinstance(cell, list) else [cell])])
		return flattened_values.nunique()

	def check_for_level_switching(self):
		# Add the new nested column to the DataFrame
		# self.df['flags', 'level_switching'] = False
		self.df[('flags', 'level_switching')] = self.df[self.HISTORY].apply(
			lambda row: '*' if self.count_unique_non_nan(row) > 1 else None, axis=1)
		return self.df[[('flags', 'level_switching')]]

	def get_history(self, dates, attendee_names):
		"""
		Get the attendance history DataFrame.

		:return: DataFrame where rows are attendees, columns are weekly attendance (True/False).
		"""
		self.df = self._generate_history(dates)

		return self.get_small_df(self.df, attendee_names)

	@classmethod
	def get_small_df(cls, attendance_df, attendee_names):
		# Identify any missing attendees and add them with default (False) attendance records
		existing_attendees = set(attendance_df.index)
		missing_attendees = list(set(attendee_names) - existing_attendees)

		# Filter the attendance_df to include only specified attendee names
		attendance_df = attendance_df[attendance_df.index.isin(attendee_names)]

		# Create a DataFrame for missing attendees with all attendance as empty list
		# Reindex the DataFrame with the new indices
		attendance_df = attendance_df.reindex(attendance_df.index.tolist() + missing_attendees)
		return attendance_df[cls.HISTORY]
