import re
import pandas as pd
from enum import Enum
import datetime


# defining string constants
START_DATE = 'start date'
END_DATE = 'end date'
EVENT_NAME = 'name'
EVENT_TYPE = 'type'
RSVPER_NAMES = 'rsvpers'
LOTTERY = 'Lottery'
ATTENDEES = 'Attendees'
WAITLIST = 'Attendees Waitlist'

SESH_CLINIC_EVENT_TOKEN = r'clinic'
SESH_RR_EVENT_TOKEN = 'round robin'
SESH_CANCELLED_EVENT_TOKEN = r'CANCELLED'

# defining regex
CANCELLATION_REASON_REGEX = r'\([^)]+\)\s*'  # capture cancellation reason in parenthesis
CANCELLED_EVENT_NAME_REGEX = rf'{SESH_CANCELLED_EVENT_TOKEN}\s+(?:{CANCELLATION_REASON_REGEX})?(?:\-\s*)?([^-]+)\s*'


class EventType(Enum):
    CLINIC = 'clinic'
    ROUNDROBIN = 'round robin'
    BALL_MACHINE_SESSION = 'Ball Machine Session'
    DUPR_MATCHES = 'DUPR Matches'
    GETTING_STARTED = 'Getting Started'
    OTHER = 'other'


class SeshData:
    # Regular expression to capture each section
    # Define patterns for readability
    # Pattern for names, allowing for quoted nicknames inside names
    nickname_pattern = r'\s+[“"”][^“"”,]+[“"”]\s+'

    curr_section_header_pattern = rf"""
        (?:\"\s*)? 		# Optionally match an opening double quote and whitespace
        ([^":]+)		# Match the section header text (any characters except " and :)
        (?:\"\s*)?		# Optionally match a closing double quote with optional whitespace
        (?:\s*:\s*)		# Ensure there is a colon (:) after the section header with optional whitespace
        """

    next_section_header_pattern = rf"""
        (?:\"\s*)? 		# Optionally match an opening double quote and whitespace
        (?:[^":]+)		# Match the section header text (any characters except " and :)
        (?:\"\s*)?		# Optionally match a closing double quote with optional whitespace
        (?:\s*:\s*)		# Ensure there is a colon (:) after the section header with optional whitespace
        """

    section_pattern = rf"""
        {curr_section_header_pattern}						# Match the current section header
        (.*?)												# Non-greedy capture everything between headers
        (?=\s*(?:,\s*{next_section_header_pattern})|$)  	# Lookahead for the next section header or end of string
        """

    def __init__(self, filename="test_data/test_data.csv"):
        if not filename.endswith('.csv'):
            raise Exception('incorrect file type, please enter a csv filename that ends with .csv')

        # Load the CSV file into a DataFrame
        try:
            self.df = pd.read_csv(filename)
        except FileNotFoundError:
            raise FileNotFoundError(f"File '{filename}' not found. Please check the file path.")
        except pd.errors.EmptyDataError:
            raise ValueError(f"The file '{filename}' is empty.")
        except pd.errors.ParserError:
            raise ValueError(f"Error parsing '{filename}'. Ensure it's a valid CSV.")
        except Exception as e:
            raise RuntimeError(f"An unexpected error occurred: {e}")

        # TODO: need to check if that accidentally drops the cancelled events
        self.df = self.df.dropna(subset=[RSVPER_NAMES, ])

        self.df[START_DATE] = pd.to_datetime(self.df[START_DATE], errors='coerce')
        self.df[START_DATE] = self.df[START_DATE].dt.date   # convert datetime to date (time is not necessary)
        self.df[RSVPER_NAMES] = self.df[RSVPER_NAMES].apply(lambda x: self.parse_rsvpers_string(x))
        self.df[EVENT_TYPE] = self.df[EVENT_NAME].apply(lambda x: self.get_event_type(x))
        self.df = self.df.sort_values(by=START_DATE, ascending=False)

        self.df = self.remove_canceled_event(self.df)

    @classmethod
    def parse_rsvpers_string(cls, rsvpers_str: str) -> dict:
        """
        Parse a string containing lists of attendees under different headers.
        Returns a dictionary with headers as keys and lists of names as values.
        :param rsvpers_str: Input string in the format "Header1: name1,name2,...,Header2: name1,name2,..."
        :return: dict: Dictionary with headers as keys and lists of names as values
        """

        result = {}
        sections = re.findall(cls.section_pattern, rsvpers_str, flags=re.VERBOSE)

        # Step 2: Find all matches using the pattern
        for section_header, section_value in sections:
            cleaned_section_value = section_value.strip(' ,"')
            names = re.split(r'\s*,\s*', cleaned_section_value)
            names = [re.sub(cls.nickname_pattern, ' ', name.strip())
                     for name in names if len(name) > 0 and not name.isspace()]
            result[section_header] = names
        return result

    @classmethod
    def get_event_type(cls, event_name):
        if re.search(r'Advanced Intermediate Clinic', event_name, re.IGNORECASE):
            return "Advanced Intermediate Clinic"
        elif re.search(r'Intermediate Clinic', event_name, re.IGNORECASE):
            return "Intermediate Clinic"
        elif re.search(r'Advanced Beginner Clinic', event_name, re.IGNORECASE):
            return "Advanced Beginner Clinic"
        elif re.search(r'Beginner Clinic', event_name, re.IGNORECASE):
            return f"Beginner Clinic"
        elif re.search(r'Round Robin - \d\.\d+ to \d\.\d+', event_name, re.IGNORECASE):
            return re.findall(r'Round Robin - \d\.\d+ to \d\.\d+', event_name, re.IGNORECASE)[0]
        elif re.search(r'DUPR Matches', event_name, re.IGNORECASE):
            return EventType.DUPR_MATCHES
        elif re.search(r'Getting Started', event_name, re.IGNORECASE):
            return EventType.GETTING_STARTED
        elif re.search(r'Ball Machine Session\s*\([0-9.,\s]+\)', event_name, re.IGNORECASE):
            return EventType.BALL_MACHINE_SESSION
        else:
            return EventType.OTHER

    @classmethod
    def remove_canceled_event(cls, df):
        """
        Identifying and removing both canceled events and their corresponding events within the previous week.
        """
        # Gather a list of canceled events based on a specific token in the event name
        cancelled_event_condition = df[EVENT_NAME].str.contains(SESH_CANCELLED_EVENT_TOKEN, case=False, na=False)
        cancelled_event_df = df[cancelled_event_condition]

        # Remove canceled events from the main DataFrame
        df = df[~cancelled_event_condition]

        indices_to_remove = []

        # Iterate over each canceled event to find related events within the last week
        for idx, cancelled_clinic_row in cancelled_event_df.iterrows():
            cancellation_date = cancelled_clinic_row[START_DATE]
            a_week_ago = cancellation_date - datetime.timedelta(days=7)
            event_type = cancelled_clinic_row[EVENT_TYPE]
            indices = df[(df[START_DATE] >= a_week_ago) &
                         (df[START_DATE] < cancellation_date) &
                         (df[EVENT_TYPE] == event_type)
                         ].index.to_list()

            # Accumulate indices of related events to remove
            indices_to_remove.extend(indices)

        # Drop the identified rows from the DataFrame
        df.drop(indices_to_remove, inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df
