import unittest
import pandas as pd
from sesh import SeshData
from lottery import Lottery  # Assuming Lottery class is saved in lottery.py


# Unit test_data class for parse_rsvpers_string
class TestParseRsvpersString(unittest.TestCase):

    def test_names_with_and_without_nicknames(self):
        input_str = '"Lottery: Doug Felt","Attendees: Jane Smith,John "Johnny" Doe,Alice "The Great" Wonderland"'
        expected_output = {
            'Lottery': ['Doug Felt'],
            'Attendees': ['Jane Smith', 'John Doe', 'Alice Wonderland']
        }
        self.assertEqual(SeshData.parse_rsvpers_string(input_str), expected_output)

    def test_empty_sections(self):
        input_str = '"Lottery: ","Attendees: "  '
        expected_output = {
            'Lottery': [],
            'Attendees': []
        }
        self.assertEqual(SeshData.parse_rsvpers_string(input_str), expected_output)

    def test_only_names_without_nicknames(self):
        input_str = '"Lottery: ","Attendees: Jane Smith,John Doe,Alice Wonderland"'
        expected_output = {
            'Lottery': [],
            'Attendees': ['Jane Smith', 'John Doe', 'Alice Wonderland']
        }
        self.assertEqual(SeshData.parse_rsvpers_string(input_str), expected_output)

    def test_mixed_names(self):
        input_str = '"Lottery: ", "Attendees: Jane Smith, Carrie "Cross-Court" Anderson, Rich Castro"'
        expected_output = {
            'Lottery': [],
            'Attendees': ['Jane Smith', 'Carrie Anderson', 'Rich Castro']
        }
        self.assertEqual(SeshData.parse_rsvpers_string(input_str), expected_output)

    def test_misplaced_double_quotes(self):
        input_str = '"Attendees: Jane Tse,Ann ODonnell,Katya Sheinin,Susan Li,Nancy Panayides,Monica Chan,' \
                    'Bianca Guerrero,Nancy Hosay,Sandy Lui,Gail Gorton,Carolyn Solomon,Cannie Seto,Art LaHait,' \
                    'Monica Stone,Beth Marer-Garcia,Megan Ancker", "Attendees Waitlist: " Teresa Flagg, ' \
                    'Gloria Taffee, Margie Harrington'
        expected_output = {
            'Attendees': ['Jane Tse', 'Ann ODonnell', 'Katya Sheinin', 'Susan Li', 'Nancy Panayides', 'Monica Chan',
                          'Bianca Guerrero', 'Nancy Hosay', 'Sandy Lui', 'Gail Gorton', 'Carolyn Solomon',
                          'Cannie Seto', 'Art LaHait', 'Monica Stone', 'Beth Marer-Garcia', 'Megan Ancker'],
            'Attendees Waitlist': ['Teresa Flagg', 'Gloria Taffee', 'Margie Harrington']
        }
        self.assertEqual(SeshData.parse_rsvpers_string(input_str), expected_output)


class TestLottery(unittest.TestCase):

    def setUp(self):
        # Sample attendance data DataFrame
        data = {
            'Attendee': ['Alice', 'Bob', 'Charlie', 'David'],
            '2024-10-01 to 2024-10-07': [True, False, True, False],
            '2024-10-08 to 2024-10-14': [False, False, True, True],
            '2024-10-15 to 2024-10-21': [True, True, False, False],
            '2024-10-22 to 2024-10-28': [False, True, False, True]
        }
        self.attendance_df = pd.DataFrame(data)
        # Reset index to add attendee names as a column
        self.attendance_df.set_index('Attendee', inplace=True)
        self.attendance_df.rename(columns={'index': 'Attendee'}, inplace=True)
        self.attendee_names = ['Alice', 'Bob', 'Charlie', 'Mary']
        self.lottery = Lottery(attendee_names=self.attendee_names,
                               attendance_df=self.attendance_df)

    def test_priority_score_calculation(self):
        # Test that priority scores are calculated correctly
        self.lottery.compute_priority()
        priority_scores = self.lottery.get_priority_scores()

        # Check that the priority scores are as expected
        for attendee, row in self.lottery.attendance_df.iterrows():
            expected_score = row.sum()  # Summing attendance to get expected score
            calculated_score = int(priority_scores.loc[attendee, 'Priority'])  # Exclude random part
            self.assertEqual(expected_score, calculated_score, f"Priority mismatch for {attendee}")

    def test_randomization_effect(self):
        # Test that adding randomization affects priority scores differently each time
        scores_1 = self.lottery.get_priority_scores()['Score'].copy()

        # Re-run the lottery to apply randomization again
        self.lottery.compute_priority()
        scores_2 = self.lottery.get_priority_scores()['Score']

        # Assert that the scores are not identical due to randomization
        self.assertFalse(scores_1.equals(scores_2), "Randomized scores should not be identical on each run")

    def test_select_winners(self):
        # Test selecting the top 16 attendees
        winners = self.lottery.select_winners(num_winners=16)

        # Ensure that winners are in the expected number
        self.assertEqual(len(winners), min(16, len(self.attendance_df)), "Incorrect number of winners selected")

        # Ensure winners are sorted by priority score
        sorted_winners = self.lottery.get_priority_scores().index[:len(winners)].tolist()
        self.assertEqual(winners, sorted_winners, "Winners are not selected by the correct priority order")

    def test_fewer_than_16_attendees(self):
        # Test behavior when fewer than 16 attendees are in the DataFrame
        small_attendance_df = self.attendance_df.head(2)  # Only 2 attendees
        attendee_names = ['Alice', 'Bob', 'Charlie', 'Mary']
        small_lottery = Lottery(attendee_names=attendee_names, attendance_df=small_attendance_df)
        winners = small_lottery.select_winners(num_winners=16)

        # Expect all attendees to be winners since we have fewer than 16
        self.assertEqual(len(winners), 4, "All attendees should be winners when fewer than 16")
        self.assertEqual(set(winners), set(attendee_names), "Winners do not match expected attendees")

    def test_all_attendees_with_zero_attendance(self):
        # Test case where all attendees have zero attendance
        zero_attendance_df = pd.DataFrame(False, index=self.attendance_df.index, columns=self.attendance_df.columns)
        attendee_names = ['Alice', 'Bob', 'Charlie', 'Mary', 'James']
        zero_lottery = Lottery(attendee_names=attendee_names, attendance_df=zero_attendance_df)
        winners = zero_lottery.select_winners(num_winners=16)

        # Expect all attendees to have equal priority (zero attendance), so they should all be eligible as winners
        self.assertEqual(len(winners), min(16, len(attendee_names)),
                         "Winners do not match expected count for zero attendance")


# Run the tests
if __name__ == '__main__':
    unittest.main()
