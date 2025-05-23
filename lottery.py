import pandas as pd
import numpy as np
import logging
from sesh import ATTENDEES, WAITLIST


class Lottery:
	PTCPNT_COL_NAME = 'Participant'
	PRIORITY_COL_NAME = 'Priority'
	SCORE_COL_NAME = 'Score'
	GROUP_COL_NAME = 'Group'
	FLAGS_COL_NAME = 'Flags'
	ATTENDANCE_COL_NAME = 'Attendance'

	def __init__(
			self,
			event_type: str,
			attendance_df: pd.DataFrame,
			max_num_attendees: int
	) -> None:
		"""
		Computes a priority score for each participant based on his/her attendance
		Orders participants based on a randomized prioritized score
		Flags individuals who are signing up for multiple lotteries and changing their levels

		:param event_type: string representing the type of event, such as "Clinic-AB"
		:param attendance_df: DataFrame with attendees as rows and weekly attendance as columns (True/False).
		:param max_num_attendees: int representing the maximum number of attendees
		"""

		self.logger = logging.getLogger(self.__class__.__name__)

		# filter attendance_df based on person_names
		self.event_type = event_type
		self.max_num_attendees = max_num_attendees

		self.priority_df = None  # This will store the DataFrame with priority scores
		self.flags_df = None

		self.attendance_df = attendance_df
		self.num_participants = self.attendance_df.shape[0]
		self.num_past_events = self.attendance_df.shape[1]

		self.participant_df = None

	def compute_priority(self):
		"""
		Compute priority scores for each attendee based on their attendance history.

		- 	Sums each row of the attendance history DataFrame to calculate the attendance score.
		- 	Lower scores represent higher priority (0 means the attendee has never attended,
			thus has the highest priority).
		- 	Adds a small random number between 0 and 1 to each score to randomize attendees with similar scores.
		- 	Creates a new DataFrame (priority_df) to store each attendee's priority score, sorted in ascending order.
		"""
		# Weighted sum of attendance (True counts as 1, False counts as 0) across columns to get the attendance score
		# Lower scores mean higher priority
		bool_attendance_df = self.attendance_df.map(lambda x: len(x) > 0 if isinstance(x, list) else 0)
		max_weight = 2 ** (self.num_past_events - 1)
		weights = [max_weight * (0.5 ** col_idx) for col_idx in range(self.num_past_events)]

		score = (bool_attendance_df * weights).sum(axis=1)

		# Add a small random number between 0 and 1 to each score for randomization among similar scores
		randomized_score = score + np.random.uniform(0, 1, size=self.num_participants)

		# Create a new DataFrame with priority scores
		priority_df = pd.DataFrame({
			self.PTCPNT_COL_NAME: self.attendance_df.index,
			self.SCORE_COL_NAME: randomized_score
		}).set_index(self.PTCPNT_COL_NAME)
		priority_df.sort_values(by=self.SCORE_COL_NAME, ascending=True, inplace=True)
		return priority_df

	def compute_flags(self, all_participants):
		# Create a new DataFrame with the same index
		flags_df = pd.DataFrame(index=self.priority_df.index)

		flags_df['level_switch'] = None
		flags_df['multi_signup'] = False

		# todo: need to update the algorithm to only check the last two sessions
		for name, row in flags_df.iterrows():
			flags_df.loc[name, 'level_switch'] = ','.join(
				self.get_diff_event_types(self.event_type, self.attendance_df.loc[name])
			)
			if name in all_participants:
				flags_df.loc[name, 'multi_signup'] = True
		return flags_df

	def get_participant_df(self):
		self.participant_df = pd.concat(
			[self.flags_df, self.priority_df, self.attendance_df],
			axis=1,
			keys=[self.FLAGS_COL_NAME, self.PRIORITY_COL_NAME, self.ATTENDANCE_COL_NAME])

		self.participant_df.sort_values(
			by=(self.PRIORITY_COL_NAME, self.SCORE_COL_NAME),
			ascending=True,
			inplace=True)

		# Set a new integer index
		self.participant_df = self.participant_df.reset_index()
		self.participant_df.index = pd.RangeIndex(start=1, stop=len(self.participant_df) + 1, step=1)
		self.participant_df.rename(columns={'index': self.PTCPNT_COL_NAME}, inplace=True)

	def select_and_sort_attendees(self, exclude_from_lottery, all_participants):
		self.priority_df = self.compute_priority()
		self.flags_df = self.compute_flags(all_participants)
		self.deprioritize_participants(exclude_from_lottery, 200)
		self.deprioritize_participants(all_participants, 100)

		self.get_participant_df()
		self.select_attendees_and_waitlist(num_participants=self.max_num_attendees)

	def select_attendees_and_waitlist(self, num_participants: int):
		"""
		Selects the top num_winners participants based on priority score and returns their names
		as the lottery attendees and put the rest of the participants on a waitlist.

		:param num_participants: Number of winners to select.
		:return: List of names of lottery winners.
		"""

		self.participant_df[self.GROUP_COL_NAME] = [
			ATTENDEES if i <= num_participants else WAITLIST
			for i in range(1, len(self.participant_df) + 1)
		]

	def get_attendee_list(self):
		return self.participant_df[self.PTCPNT_COL_NAME].tolist()

	def deprioritize_participants(self, participants, priority):
		if len(participants) == 0:
			return
		event_participants = self.priority_df.index.tolist()
		for participant in event_participants:
			if participant in participants:
				self.priority_df.loc[participant] = priority

	@staticmethod
	def shorten_event_type(event_type):
		return event_type.split('-', maxsplit=1)[1]

	def get_diff_event_types(self, event_type, row):
		# todo: this would need to be handled in clinic_lottery.py since different events
		#  needs different ways of handling
		row = row.dropna()
		attended_event_types = [item for cell in row for item in (cell if isinstance(cell, list) else [cell])]
		flattened_values = set([
			self.shorten_event_type(attended_event_type) for attended_event_type in attended_event_types
			if attended_event_type != event_type
		])

		flattened_values = list(flattened_values)
		return flattened_values
