import pandas as pd
import numpy as np

import datetime
from sesh import SeshData, SESH_CANCELLED_EVENT_TOKEN, SESH_CLINIC_EVENT_TOKEN
from sesh_util import remove_canceled_event, convert_date_str_to_obj


class ClinicEvents:
	def __init__(self, df):
		self.df = df
		self.df = self.df[[SeshData.EVENT_NAME, SeshData.START_DATE, SeshData.RSVPER_NAMES]]

		clinic_set_df = self.df[
			self.df[SeshData.EVENT_NAME].str.contains(SESH_CLINIC_EVENT_TOKEN, case=False, na=False)
		]
		# gather a list of cancelled clinic events
		cancelled_condition = clinic_set_df[SeshData.EVENT_NAME].str.contains(SESH_CANCELLED_EVENT_TOKEN, case=False, na=False)
		cancelled_clinic_set_df = clinic_set_df[cancelled_condition]
		clinic_set_df = clinic_set_df[~cancelled_condition]

		self.df = remove_canceled_event(cancelled_clinic_set_df, clinic_set_df)

	@classmethod
	def filter_by_level(cls, df, level):
		# TODO: not robust enough
		df = df[df[SeshData.EVENT_NAME].str.contains(level, case=False, na=False)]
		return df

	def get_event(self, level, event_date):
		df = self.df[self.df[SeshData.START_DATE] == event_date]
		df = self.filter_by_level(df, level)
		return df.head(1)

	def get_latest_events(self, level, event_date=None, max_sessions=3):
		if event_date is None:
			event_date = datetime.date.today()
		elif isinstance(event_date, str):
			event_date = convert_date_str_to_obj(event_date)
		elif not isinstance(event_date, datetime.date):
			raise TypeError(f'event_date {event_date} needs to be of type(datetime.date)')

		self.df = self.df[self.df[SeshData.START_DATE] < event_date]

		df = self.filter_by_level(self.df, level)
		df = df.sort_values(
			by=SeshData.START_DATE,
			ascending=False
		)

		# Get the date of the first and last sessions within the first max_sessions rows
		df = df.head(max_sessions)
		last_session_date = df.head(1)[SeshData.START_DATE].iloc[0]
		first_session_date = df.tail(1)[SeshData.START_DATE].iloc[0]

		df = df[
			(df[SeshData.START_DATE] >= first_session_date) &
			(df[SeshData.START_DATE] <= last_session_date)
		]
		return df


class AttendanceHistory:
	ATTENDEE_COL_NAME = 'Attendee'

	def __init__(self, dates, events_df):
		"""
		Initialize the AttendanceHistory with a list of dates and a DataFrame of events.

		:param dates:	List of datetime objects representing the dates to evaluate.
		:param events_df: DataFrame with 'start_date' column (date) and 'Attendees' column (list of attendee names).
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
				(self.events_df[SeshData.START_DATE] >= week_range[0].date()) &
				(self.events_df[SeshData.START_DATE] <= week_range[-1].date())
				]
			# Collect unique attendees for the week
			attendees_in_week = set([
				attendee
				for rsvper_names in events_in_week[SeshData.RSVPER_NAMES]
				for attendee in rsvper_names.get(SeshData.ATTENDEES, [])	# TODO: run into a problem when attendees key doesn't exist
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
		return attendance_df

	def get_df(self):
		"""
		Get the attendance history DataFrame.

		:return: DataFrame where rows are attendees, columns are weekly attendance (True/False).
		"""
		return self.attendance_df


class Lottery:
	def __init__(self, attendee_names, attendance_df):
		"""
		Initialize the Lottery with an attendance history DataFrame.

		:param attendee_names: List of attendee names to include in the lottery.
		:param attendance_df: DataFrame with attendees as rows and weekly attendance as columns (True/False).
		"""

		# Identify any missing attendees and add them with default (False) attendance records
		existing_attendees = set(attendance_df.index)
		missing_attendees = set(attendee_names) - existing_attendees

		# Create a DataFrame for missing attendees with all attendance as False
		if missing_attendees:
			missing_df = pd.DataFrame({AttendanceHistory.ATTENDEE_COL_NAME: list(missing_attendees)})
			missing_df.set_index(AttendanceHistory.ATTENDEE_COL_NAME, inplace=True)

			for col in attendance_df.columns:
				missing_df[col] = False  # Set all attendance to False
			# Append the missing attendees to the original attendance DataFrame
			# attendance_df = pd.concat([attendance_df, missing_df], ignore_index=True)
			attendance_df = pd.concat([attendance_df, missing_df])

			# Ensure 'Attendee' column is set as the index for priority computation and access

		# Filter the attendance_df to include only specified attendee names
		self.attendance_df = attendance_df[
			attendance_df.index.isin(attendee_names)]
		# self.attendance_df.set_index(AttendanceHistory.ATTENDEE_COL_NAME, inplace=True)

		print(self.attendance_df)
		# filter attendance_df based on person_names
		self.priority_df = None  # This will store the DataFrame with priority scores

	def compute_priority(self):
		"""
		Compute priority scores for each attendee based on their attendance history.

		- 	Sums each row of the attendance history DataFrame to calculate the attendance score.
		- 	Lower scores represent higher priority (0 means the attendee has never attended,
			thus has the highest priority).
		- 	Adds a small random number between 0 and 1 to each score to randomize attendees with similar scores.
		- 	Creates a new DataFrame (priority_df) to store each attendee's priority score, sorted in ascending order.
		"""
		# Sum attendance (True counts as 1, False counts as 0) across columns to get the attendance score
		# Lower scores mean higher priority
		attendance_score = self.attendance_df.sum(axis=1)

		# Add a small random number between 0 and 1 to each score for randomization among similar scores
		randomized_score = attendance_score + np.random.uniform(0, 1, size=len(self.attendance_df))

		# Create a new DataFrame with priority scores
		self.priority_df = pd.DataFrame({
			'Attendee': self.attendance_df.index,
			'Priority': attendance_score,
			'Score': randomized_score
		}).set_index(AttendanceHistory.ATTENDEE_COL_NAME)

		# Sort by priority score in ascending order (the lowest score has the highest priority)
		self.priority_df.sort_values(by='Score', ascending=True, inplace=True)

	def select_winners(self, num_winners=16):
		"""
		Selects the top num_winners attendees based on priority score and returns their names as the lottery winners.

		:param num_winners: Number of winners to select.
		:return: List of names of lottery winners.
		"""
		if self.priority_df is None:
			self.compute_priority()  # Ensure priority scores are computed

		# Select the top attendees as winners
		winners = self.priority_df.head(num_winners).index.tolist()
		return winners

	def get_priority_scores(self):
		"""
		Get the DataFrame of attendees with priority scores.


		:return: 	Returns the DataFrame with priority scores for reference,
					allowing you to inspect the prioritized list of attendees.
		"""
		if self.priority_df is None:
			self.compute_priority()
		return self.priority_df


if __name__ == '__main__':
	sesh_data = SeshData('test_data/test.csv')
	date_str = '2023-05-24'
	clinic_level = '3.5'

	date = convert_date_str_to_obj(date_str)
	clinic_sessions = ClinicEvents(sesh_data.df)
	clinic_session = clinic_sessions.get_event(event_date=date, level=clinic_level)
	clinic_sessions_by_level = clinic_sessions.get_latest_events(event_date=date, level=clinic_level)

	names = clinic_session[SeshData.RSVPER_NAMES].iloc[0].get(SeshData.ATTENDEES, [])
	last_n_dates = clinic_sessions_by_level[SeshData.START_DATE].to_list()
	attendance_history = AttendanceHistory(last_n_dates, clinic_sessions.df)
	print('names:', names)
	lottery = Lottery(attendee_names=names, attendance_df=attendance_history.get_df())
	winners = lottery.select_winners()
	print(lottery.priority_df)
	print('winnners:', winners)
