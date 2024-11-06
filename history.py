import datetime
from enum import Enum
import pandas as pd
from sesh import START_DATE, RSVPER_NAMES, ATTENDEES


class AttendanceHistory:
	ATTENDEE_COL_NAME = 'Attendee'

	def __init__(self, dates, events_df):
		"""
		Initialize the AttendanceHistory with a list of dates and a DataFrame of events.

		:param dates:		List of datetime objects representing the dates to evaluate.
		:param events_df: 	DataFrame with 'event_name' (name of event), 'start_date' column (date)
							and 'Attendees' column (list of attendee names).

		"""
		self.dates = dates
		self.events_df = events_df.copy()
		self.attendance_df = self._generate_attendance_history()

	@classmethod
	def _get_week_date_range(cls, event_date):
		"""
		Get the start and end dates of the week (Monday to Sunday) for a given date.

		:param event_date: The specific date to find the week range for.
		:return: date_range(start=start_of_week, periods=7)
		"""
		# Calculate the start of the week (Monday)
		start_of_week = event_date - datetime.timedelta(days=event_date.weekday())
		week_range = pd.date_range(start=start_of_week, periods=7)
		return week_range

	def _generate_attendance_history(self):
		"""
		Generate the attendance history DataFrame with attendees as rows and weekly attendance as columns.

		:return: DataFrame where rows are attendees, columns are weekly attendance (True/False).
		"""
		# Initialize an empty dictionary to hold weekly attendance records for each attendee
		attendance_data = {}

		for event_date in self.dates:
			# Determine the week date range as a Pandas date range
			week_range = self._get_week_date_range(event_date)
			week_label = f"{week_range[0].date()} to {week_range[-1].date()}"

			# Filter events within this week's range
			events_in_week = self.events_df[
				(self.events_df[START_DATE] >= week_range[0].date()) &
				(self.events_df[START_DATE] <= week_range[-1].date())
				]

			# Collect unique attendees for the week
			attendees_in_week = set([
				attendee
				for rsvper_names in events_in_week[RSVPER_NAMES]
				for attendee in rsvper_names.get(ATTENDEES, [])		# TODO: run into a problem when attendees key doesn't exist
			])

			# Update the attendance data dictionary
			for attendee in attendees_in_week:
				if attendee not in attendance_data:
					attendance_data[attendee] = {}
				attendance_data[attendee][week_label] = True

			# Mark attendees who did not attend in the week as False
			for attendee in attendance_data:
				if week_label not in attendance_data[attendee]:
					attendance_data[attendee][week_label] = False

		# Convert the attendance data dictionary to a DataFrame
		attendance_df = pd.DataFrame.from_dict(attendance_data, orient='index').fillna(0).astype(bool)

		# Reset index to add attendee names as a column
		attendance_df.reset_index(inplace=True)
		attendance_df.rename(columns={'index': self.ATTENDEE_COL_NAME}, inplace=True)
		attendance_df.set_index(self.ATTENDEE_COL_NAME, inplace=True)

		return attendance_df

	def get_df(self, attendee_names=None):
		"""
		Get the attendance history DataFrame.

		:return: DataFrame where rows are attendees, columns are weekly attendance (True/False).
		"""
		if attendee_names is None:
			return self.attendance_df
		else:
			return self.get_small_df(self.attendance_df, attendee_names)


	@classmethod
	def get_small_df(cls, attendance_df, attendee_names):
		# Identify any missing attendees and add them with default (False) attendance records
		existing_attendees = set(attendance_df.index)
		missing_attendees = list(set(attendee_names) - existing_attendees)

		# Filter the attendance_df to include only specified attendee names
		attendance_df = attendance_df[attendance_df.index.isin(attendee_names)]

		# Create a DataFrame for missing attendees with all attendance as False
		if missing_attendees:
			missing_df = pd.DataFrame({cls.ATTENDEE_COL_NAME: missing_attendees})
			# Ensure 'Attendee' column is set as the index for priority computation and access
			missing_df.set_index(cls.ATTENDEE_COL_NAME, inplace=True)

			for col in attendance_df.columns:
				missing_df[col] = False  # Set all attendance to False

			# Append the missing attendees to the original attendance DataFrame
			attendance_df = pd.concat([attendance_df, missing_df])

		return attendance_df
