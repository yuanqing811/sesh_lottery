import unittest
import pandas as pd
from sesh import SeshData, ATTENDEES, WAITLIST, EVENT_NAME, EVENT_TYPE, START_DATE, RSVPER_NAMES
from history import AttendanceHistory
from lottery import Lottery  # Assuming Lottery class is saved in lottery.py
import datetime
from event import ClinicEventManager
from sesh_util import convert_date_str_to_obj


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

    def test_case1(self):
        input_str = '"Lottery: Tami Tran,Min Chung",' \
                    '"Attendees: Lisa Shea,Jian Yin,Linda Atwood,Alex Woo,Becky Sarabia,Katie Peng,' \
                    'Mehrnaz Hada,Janet Berkowitz,May Yick,Doug Felt,Sabrina Lin,Mora Kan,Jeanne Hsu,' \
                    'Diana Friedman,Jay Gitterman,Hui (Helen) Li",' \
                    '"Attendees Waitlist: " Amy Jiang,Ellen Jaworski,Kathleen Lund,Ivy Tam,Helen Wong,' \
                    'Susan Hanson,Maralissa Thomas,Keri Lung,Anne Silverstein,Elena Chiu,Victor Roytburd,' \
                    'Meri Gruber'
        expected_output = {
            'Lottery': ['Tami Tran', 'Min Chung'],
            'Attendees': ['Lisa Shea', 'Jian Yin', 'Linda Atwood', 'Alex Woo', 'Becky Sarabia', 'Katie Peng',
                          'Mehrnaz Hada', 'Janet Berkowitz', 'May Yick', 'Doug Felt', 'Sabrina Lin', 'Mora Kan',
                          'Jeanne Hsu', 'Diana Friedman', 'Jay Gitterman', 'Hui (Helen) Li', ],
            'Attendees Waitlist': ['Amy Jiang', 'Ellen Jaworski', 'Kathleen Lund', 'Ivy Tam', 'Helen Wong',
                                   'Susan Hanson', 'Maralissa Thomas', 'Keri Lung', 'Anne Silverstein',
                                   'Elena Chiu', 'Victor Roytburd', 'Meri Gruber']
        }
        self.assertEqual(SeshData.parse_rsvpers_string(input_str), expected_output)


class TestRemoveCanceledEvent(unittest.TestCase):

    def setUp(self):
        # Create a sample DataFrame with event data

        data = {
            EVENT_NAME: [
                'Round Robins - NO EVENT THIS WEEK',
                'CANCELLED - Advanced Intermediate Clinic(3.5) - HOLIDAY WK',
                'Ball Machine Session(3.0, 3.25, 3.5)',
                'Ball Machine Session(3.0, 3.25, 3.5)',
                'CANCELLED - Intermediate Clinic(3.25) - HOLIDAY WK',
                'Ball Machine Session(3.0, 3.25)',
                'Ball Machine Session(All levels)',
                'CANCELLED - Beginner Clinic(2.0 to 2.5) - HOLIDAY WK',
                'Ball Machine Session(3.25, 3.5, 3.75)',
                'CANCELLED - Advanced Beginner Clinic(2.75 to 3.0) - HOLIDAY WK',
                'Getting Started',
                'Youth Pickleball Meetup',
                'Sunday Early Worms Ladder',
                'DUPR Matches 2.75 to 3.75',
                'Youth Pickleball Meetup',
                'Round Robin - 3.25 to 3.75',
                'Round Robin - 2.5 to 3.0',
                'Ball Machine Session (3.0, 3.25)',
                'Advanced Intermediate Clinic (3.5)',
                'Ball Machine Session (3.25, 3.5, 3.75)',
                'Intermediate Clinic (3.25)',
                'Ball Machine Session (3.25, 3.5, 3.75)',
                'Beginner Clinic (2.0 to 2.5)',
                'Advanced Beginner Clinic (2.75 to 3.0)',
            ],
            EVENT_TYPE: [
                'Round Robin',
                'Advanced Intermediate Clinic',
                'Ball Machine Session',
                'Ball Machine Session',
                'Intermediate Clinic',
                'Ball Machine Session',
                'Ball Machine Session',
                'Beginner Clinic',
                'Ball Machine Session',
                'Advanced Beginner Clinic',
                'Getting Started',
                'other',
                'other',
                'DUPR Matches',
                'other',
                'Round Robin - 3.25 to 3.75',
                'Round Robin - 2.5 to 3.0',
                'Ball Machine Session',
                'Advanced Intermediate Clinic',
                'Ball Machine Session',
                'Intermediate Clinic',
                'Ball Machine Session',
                'Beginner Clinic',
                'Advanced Beginner Clinic',
            ],
            START_DATE: [
                datetime.datetime(2024, 7, 4),
                datetime.datetime(2024, 7, 3),
                datetime.datetime(2024, 7, 3),
                datetime.datetime(2024, 7, 2),
                datetime.datetime(2024, 7, 2),
                datetime.datetime(2024, 7, 2),
                datetime.datetime(2024, 7, 1),
                datetime.datetime(2024, 7, 1),
                datetime.datetime(2024, 7, 1),
                datetime.datetime(2024, 7, 1),
                datetime.datetime(2024, 7, 1),
                datetime.datetime(2024, 6, 30),
                datetime.datetime(2024, 6, 30),
                datetime.datetime(2024, 6, 28),
                datetime.datetime(2024, 6, 28),
                datetime.datetime(2024, 6, 27),
                datetime.datetime(2024, 6, 27),
                datetime.datetime(2024, 6, 27),
                datetime.datetime(2024, 6, 26),
                datetime.datetime(2024, 6, 25),
                datetime.datetime(2024, 6, 25),
                datetime.datetime(2024, 6, 24),
                datetime.datetime(2024, 6, 24),
                datetime.datetime(2024, 6, 24),
            ]
        }
        self.df = pd.DataFrame(data)

        # Mock the get_cancelled_event_name method to remove " - CANCELED"

    def test_remove_canceled_event(self):
        # Execute the remove_canceled_event method
        self.df = SeshData.remove_canceled_event(self.df)

        # Expected DataFrame after removing canceled events and related events
        expected_data = {
            EVENT_NAME: [
                'Round Robins - NO EVENT THIS WEEK',
                'Ball Machine Session(3.0, 3.25, 3.5)',
                'Ball Machine Session(3.0, 3.25, 3.5)',
                'Ball Machine Session(3.0, 3.25)',
                'Ball Machine Session(All levels)',
                'Ball Machine Session(3.25, 3.5, 3.75)',
                'Getting Started',
                'Youth Pickleball Meetup',
                'Sunday Early Worms Ladder',
                'DUPR Matches 2.75 to 3.75',
                'Youth Pickleball Meetup',
                'Round Robin - 3.25 to 3.75',
                'Round Robin - 2.5 to 3.0',
                'Ball Machine Session (3.0, 3.25)',
                'Ball Machine Session (3.25, 3.5, 3.75)',
                'Ball Machine Session (3.25, 3.5, 3.75)',
            ],
            EVENT_TYPE: [
                'Round Robin',
                'Ball Machine Session',
                'Ball Machine Session',
                'Ball Machine Session',
                'Ball Machine Session',
                'Ball Machine Session',
                'Getting Started',
                'other',
                'other',
                'DUPR Matches',
                'other',
                'Round Robin - 3.25 to 3.75',
                'Round Robin - 2.5 to 3.0',
                'Ball Machine Session',
                'Ball Machine Session',
                'Ball Machine Session',
            ],
            START_DATE: [
                datetime.datetime(2024, 7, 4),
                datetime.datetime(2024, 7, 3),
                datetime.datetime(2024, 7, 2),
                datetime.datetime(2024, 7, 2),
                datetime.datetime(2024, 7, 1),
                datetime.datetime(2024, 7, 1),
                datetime.datetime(2024, 7, 1),
                datetime.datetime(2024, 6, 30),
                datetime.datetime(2024, 6, 30),
                datetime.datetime(2024, 6, 28),
                datetime.datetime(2024, 6, 28),
                datetime.datetime(2024, 6, 27),
                datetime.datetime(2024, 6, 27),
                datetime.datetime(2024, 6, 27),
                datetime.datetime(2024, 6, 25),
                datetime.datetime(2024, 6, 24),
            ]
        }
        expected_df = pd.DataFrame(expected_data)

        # Compare the result with the expected DataFrame
        pd.testing.assert_frame_equal(self.df.reset_index(drop=True), expected_df.reset_index(drop=True))


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
        self.lottery = Lottery(attendance_df=self.attendance_df)

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
        num_winners = 16
        winners = self.lottery.select_winners(num_winners=num_winners)
        attendees = winners[ATTENDEES]
        waitlist = winners[WAITLIST]

        # Ensure that winners are in the expected number
        self.assertEqual(len(attendees), min(num_winners, len(self.attendance_df)),
                         "Incorrect number of winners selected")
        self.assertEqual(len(waitlist),
                         0 if len(self.attendance_df) <= num_winners else (len(self.attendance_df)-num_winners),
                         "Incorrect number of winners selected")

        # Ensure winners are sorted by priority score
        sorted_winners = self.lottery.get_priority_scores().index[:num_winners].tolist()
        self.assertEqual(attendees, sorted_winners, "Winners are not selected by the correct priority order")

    def test_fewer_than_16_attendees(self):
        small_attendance_size = 2
        num_winners = 16
        # Test behavior when fewer than 16 attendees are in the DataFrame
        small_attendance_df = self.attendance_df.head(small_attendance_size)  # Only 2 attendees
        attendee_names = ['Alice', 'Bob', 'Charlie', 'Mary']
        df = AttendanceHistory.get_small_df(attendance_df=small_attendance_df, attendee_names=attendee_names)
        small_lottery = Lottery(attendance_df=df)
        winners = small_lottery.select_winners(num_winners=num_winners)
        attendees = winners[ATTENDEES]
        waitlist = winners[WAITLIST]
        # Expect all attendees to be winners since we have fewer than 16
        self.assertEqual(len(attendees), len(attendee_names), "All attendees should be winners when fewer than 16")
        self.assertEqual(set(attendees), set(attendee_names), "Winners do not match expected attendees")
        self.assertEqual(len(waitlist), 0)

    def test_all_attendees_with_zero_attendance(self):
        num_winners = 16
        # Test case where all attendees have zero attendance
        zero_attendance_df = pd.DataFrame(False, index=self.attendance_df.index, columns=self.attendance_df.columns)
        attendee_names = ['Alice', 'Bob', 'Charlie', 'Mary', 'James']
        df = AttendanceHistory.get_small_df(attendance_df=zero_attendance_df, attendee_names=attendee_names)
        zero_lottery = Lottery(attendance_df=df)
        winners = zero_lottery.select_winners(num_winners=num_winners)
        attendees = winners[ATTENDEES]
        waitlist = winners[WAITLIST]

        if len(attendee_names) <= num_winners:
            # Expect all attendees to have equal priority (zero attendance), so they should all be eligible as winners
            self.assertEqual(len(attendees), len(attendee_names),
                             "Winners do not match expected count for zero attendance")
            self.assertEqual(len(waitlist), 0)
        else:
            self.assertEqual(len(attendees), num_winners,
                             "Winners do not match expected count for zero attendance")
            self.assertEqual(len(waitlist), len(attendee_names) - num_winners)


class TestCompleteLottery(unittest.TestCase):
    def setUp(self) -> None:
        sesh_data = SeshData('test_data/test.csv')
        self.manager = ClinicEventManager(sesh_data.df)

    def check(self, event_date, event_type):
        # recreate signup list from old data
        event = self.manager.get_event(event_date=event_date, event_type=event_type)
        rsvper_names = event[RSVPER_NAMES].iloc[0]
        names = rsvper_names.get(ATTENDEES, [])

        events = self.manager.get_latest_events(event_date=event_date, event_type=event_type)
        last_n_dates = events[START_DATE].to_list()
        attendance_history = AttendanceHistory(last_n_dates, self.manager.df)
        sm_df = attendance_history.get_df(names)
        with pd.option_context('display.max_columns', None):
            print(sm_df)
        lottery = Lottery(attendance_df=sm_df)
        lottery.compute_priority()

        priority_df = lottery.priority_df.reindex(names)
        with pd.option_context('display.max_columns', None):
            print(priority_df)
        is_ascending = priority_df['Priority'].is_monotonic_increasing
        self.assertEqual(is_ascending, True)

    def test_priority_computation_case1(self):
        event_date = convert_date_str_to_obj('2024-06-11')
        event_type = 'Intermediate Clinic'
        self.check(event_date, event_type)

    def test_priority_computation_case2(self):
        event_date = convert_date_str_to_obj('2024-06-04')
        event_type = 'Intermediate Clinic'
        self.check(event_date, event_type)

    def test_priority_computation_case3(self):
        event_date = convert_date_str_to_obj('2024-05-21')
        event_type = 'Intermediate Clinic'
        self.check(event_date, event_type)

    def test_priority_computation_case4(self):
        event_date = convert_date_str_to_obj('2024-04-23')
        event_type = 'Intermediate Clinic'
        self.check(event_date, event_type)


# Run the tests
if __name__ == '__main__':
    unittest.main()
