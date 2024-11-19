import datetime
import pandas as pd
from sesh import START_DATE, RSVPER_NAMES, EVENT_TYPE
from sesh_util import ADV_BEG_CLINIC, ADV_INT_CLINIC, BEG_CLINIC, INT_CLINIC
from logging_config import log_dataframe_info


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
		df_index = pd.Index([], name=self.PARTICIPANT)
		self.df = pd.DataFrame(index=df_index)
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

	def _generate_history_for_date_range(self, date_range) -> None:
		# Initialize an empty dictionary to hold attendance records for each attendee
		attendance_data = {}

		date_range_label = f"{date_range[0].date()} to {date_range[-1].date()}"

		events_in_date_range = self.events_df[
			(self.events_df[START_DATE] >= date_range[0].date()) &
			(self.events_df[START_DATE] <= date_range[-1].date())
			]

		for idx, event in events_in_date_range.iterrows():
			attendees_in_event = event[RSVPER_NAMES]
			if not isinstance(attendees_in_event, list):
				continue
			# Update the attendance data dictionary
			for attendee in attendees_in_event:
				if attendee not in attendance_data:
					attendance_data[attendee] = {}
				if date_range_label not in attendance_data[attendee]:
					attendance_data[attendee][date_range_label] = []
				attendance_data[attendee][date_range_label].append(event[EVENT_TYPE])

		# Convert the attendance data dictionary to a DataFrame
		df = pd.DataFrame.from_dict(attendance_data, orient='index')
		self.df = pd.concat([self.df, df], axis=1, join='outer')
		self.df = self.df[sorted(self.df.columns, reverse=True)]

	def _generate_history(self, dates) -> pd.DataFrame:
		"""
		Generate the history DataFrame with attendees as rows and weekly attendance as columns.

		:return: DataFrame where rows are attendees, columns are weekly attendance (True/False).
		"""

		dates = sorted(dates, reverse=True)
		date_range_labels = []

		for event_date in dates:
			date_range = self._get_week_date_range(event_date)
			date_range_label = f"{date_range[0].date()} to {date_range[-1].date()}"
			date_range_labels.append(date_range_label)

			if date_range_label not in self.df.columns:
				self._generate_history_for_date_range(date_range)

		attendance_df = self.df[date_range_labels].copy()
		return attendance_df

	def get_history(self, dates, attendee_names):
		"""
		Get the attendance history DataFrame.

		:return: DataFrame where rows are attendees, columns are weekly attendance (True/False).
		"""
		df = self._generate_history(dates)
		df.columns = pd.MultiIndex.from_product([[self.HISTORY], df.columns])
		return self._get_small_df(df, attendee_names)

	@classmethod
	def _get_small_df(cls, attendance_df, attendee_names):
		# Identify any missing attendees and add them with default (False) attendance records
		existing_attendees = set(attendance_df.index)
		missing_attendees = list(set(attendee_names) - existing_attendees)

		# Filter the attendance_df to include only specified attendee names
		attendance_df = attendance_df[attendance_df.index.isin(attendee_names)]

		# Create a DataFrame for missing attendees with all attendance as empty list
		# Reindex the DataFrame with the new indices
		attendance_df = attendance_df.reindex(attendance_df.index.tolist() + missing_attendees)
		return attendance_df[cls.HISTORY]
