import pandas as pd
import numpy as np
import logging
from sesh import ATTENDEES, WAITLIST
from utils import generate_unique_filename


class Lottery:
	PTCPNT_COL = 'Participant'
	SCORE_COL = 'Score'
	COUNT_COL = 'Count'
	PRIORITY_COL = 'Priority'

	def __init__(self, event_type: str, attendance_df: pd.DataFrame, low_priority_participants: list) -> None:
		"""
		Computes a priority score for each participant based on his/her attendance
		Orders participants based on a randomized prioritized score
		Flags individuals who are signing up for multiple lotteries and changing their levels

		:param event_type: string representing the type of event, such as "Clinic-AB"
		:param attendance_df: DataFrame with attendees as rows and weekly attendance as columns (True/False).
		:param low_priority_participants: list of strings representing a list of people who should be deprioritized
		"""

		self.logger = logging.getLogger(self.__class__.__name__)

		# filter attendance_df based on person_names
		self.event_type = event_type
		self.attendance_df = attendance_df
		self.low_priority_participants = low_priority_participants
		self.num_attendees = self.attendance_df.shape[0]
		self.num_past_events = self.attendance_df.shape[1]
		self.priority_df = None  # This will store the DataFrame with priority scores
		self.flags_df = None
		self.attendee_stats_df = None
		self.result = None

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
		attendance_count = bool_attendance_df.sum(axis=1)
		max_weight = 2 ** (self.num_past_events - 1)
		weights = [max_weight * (0.5 ** col_idx) for col_idx in range(self.num_past_events)]
		attendance_score = (bool_attendance_df * weights).sum(axis=1)

		# Add a small random number between 0 and 1 to each score for randomization among similar scores
		randomized_score = attendance_score + np.random.uniform(0, 1, size=self.num_attendees)

		# Create a new DataFrame with priority scores
		self.priority_df = pd.DataFrame({
			self.PTCPNT_COL: self.attendance_df.index,
			self.COUNT_COL: attendance_count,
			self.PRIORITY_COL: attendance_score,
			self.SCORE_COL: randomized_score
		}).set_index(self.PTCPNT_COL)

		# Sort by priority score in ascending order (the lowest score has the highest priority)
		self.priority_df.sort_values(by='Score', ascending=True, inplace=True)

	def select_attendees_and_waitlist(self, num_participants: int, write_to_csv=None):
		"""
		Selects the top num_winners participants based on priority score and returns their names
		as the lottery attendees and put the rest of the participants on a waitlist.

		:param num_participants: Number of winners to select.
		:param write_to_csv: if not None, the attendee statistics will be written to a csv file.
		:return: List of names of lottery winners.
		"""

		if self.priority_df is None:
			self.compute_priority()  # Ensure priority scores are computed
			self.lower_participant_priorities()
			self.flag_participants()

		self.attendee_stats_df = pd.concat(
			[self.flags_df, self.priority_df, self.attendance_df, ],
			axis=1, keys=['flags', 'priority', 'attendance'])

		# Set a new integer index
		self.attendee_stats_df = self.attendee_stats_df.reset_index()
		self.attendee_stats_df.index = pd.RangeIndex(start=1, stop=len(self.attendee_stats_df) + 1, step=1)
		self.attendee_stats_df.rename(columns={'index': self.PTCPNT_COL}, inplace=True)

		nested_index = [
			(ATTENDEES if i <= num_participants else WAITLIST, i)
			for i in range(1, len(self.attendee_stats_df)+1)]
		nested_index = pd.MultiIndex.from_tuples(nested_index, names=["Group", "Index"])
		self.attendee_stats_df.index = nested_index

		if write_to_csv is not None:
			self.logger.info("Writing the lottery participants' statistics to a csv file")
			write_to_csv = generate_unique_filename(write_to_csv)
			self.attendee_stats_df.to_csv(write_to_csv, index=True)

	def set_priority(self, attendee, priority):
		self.priority_df.loc[attendee] = priority

	def lower_participant_priorities(self):
		event_participants = self.priority_df.index.tolist()
		for participant in event_participants:
			if participant in self.low_priority_participants:
				self.set_priority(participant, priority=100)

	def flag_participants(self):
		# check participants for level switching
		lottery_participants = self.priority_df.index.tolist()
		multi_signup_df = pd.DataFrame(index=lottery_participants)
		multi_signup_df['multi_signup'] = [
			"*" if partcipant in self.low_priority_participants else
			None for partcipant in lottery_participants
		]

		level_switch_df = pd.DataFrame(index=self.attendance_df.index.tolist())
		level_switch_df['level_switch'] = [
			'*' if self.count_unique_non_nan(row) > 1 else None
			for idx, row in self.attendance_df.iterrows()
		]

		self.flags_df = pd.concat([multi_signup_df, level_switch_df], join='outer', axis=1)

	def get_priority_scores(self):
		"""
		Get the DataFrame of attendees with priority scores.


		:return: 	Returns the DataFrame with priority scores for reference,
					allowing you to inspect the prioritized list of attendees.
		"""
		if self.priority_df is None:
			self.compute_priority()
		return self.priority_df

	def count_unique_non_nan(self, row):
		row = row.dropna()
		attended_event_types = [item for cell in row for item in (cell if isinstance(cell, list) else [cell])]
		flattened_values = set(attended_event_types + [self.event_type])
		return len(flattened_values)

