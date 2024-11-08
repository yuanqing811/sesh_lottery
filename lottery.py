import pandas as pd
import numpy as np

from history import AttendanceHistory
from sesh import ATTENDEES, WAITLIST


class Lottery:
	def __init__(self, attendance_df):
		"""
		Initialize the Lottery with an attendance history DataFrame.

		:param attendance_df: DataFrame with attendees as rows and weekly attendance as columns (True/False).
		"""

		# filter attendance_df based on person_names
		self.attendance_df = attendance_df
		self.priority_df = None  # This will store the DataFrame with priority scores
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
		# self.attendance_df.reindex(self.priority_df.index.to_list())
		self.attendee_stats_df = pd.concat([self.priority_df, self.attendance_df, ], axis=1)

		# Set a new integer index
		self.attendee_stats_df = self.attendee_stats_df.reset_index()
		self.attendee_stats_df.rename(columns={'index': 'rsvper_names'}, inplace=True)
		# self.attendee_stats_df.reset_index(drop=True, inplace=True)

	def select_winners(self, num_winners=16):
		"""
		Selects the top num_winners attendees based on priority score and returns their names as the lottery winners.

		:param num_winners: Number of winners to select.
		:return: List of names of lottery winners.
		"""
		if self.priority_df is None:
			self.compute_priority()  # Ensure priority scores are computed

		# Select the top rsvpers as attendees and assign the rest to waitlist
		priority_list = self.priority_df.index.tolist()
		if len(priority_list) <= num_winners:
			attendee_list = priority_list
			waitlist = []
		else:
			attendee_list = priority_list[:num_winners]
			waitlist = priority_list[num_winners:]
		self.result = {ATTENDEES: attendee_list, WAITLIST: waitlist}

	def get_priority_scores(self):
		"""
		Get the DataFrame of attendees with priority scores.


		:return: 	Returns the DataFrame with priority scores for reference,
					allowing you to inspect the prioritized list of attendees.
		"""
		if self.priority_df is None:
			self.compute_priority()
		return self.priority_df

