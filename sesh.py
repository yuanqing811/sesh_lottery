import re
import pandas as pd

START_DATE = 'start date'
END_DATE = 'end date'
EVENT_NAME = 'name'
RSVPER_NAMES = 'rsvpers'
LOTTERY = 'Lottery'
ATTENDEES = 'Attendees'
WAITLIST = 'Attendees Waitlist'

SESH_CLINIC_EVENT_TOKEN = r'clinic'
SESH_CANCELLED_EVENT_TOKEN = r'CANCELLED'

# defining regex
cancellation_reason = r'\([^)]+\)'  # capture cancellation in parenthesis
cancelled_event_name_regex = rf'^\s*{SESH_CANCELLED_EVENT_TOKEN}\s+(?:\-\s*)?(.+)\s*$'


class SeshData:
    START_DATE = 'start date'
    END_DATE = 'end date'
    EVENT_NAME = 'name'
    RSVPER_NAMES = 'rsvpers'
    LOTTERY = 'Lottery'
    ATTENDEES = 'Attendees'
    WAITLIST = 'Attendees Waitlist'

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

    def __init__(self, filename="test_data/test_data.csv", debug=False):
        if not filename.endswith('.csv'):
            raise Exception('incorrect file type, please enter a csv filename that ends with .csv')

        # Load the CSV file into a DataFrame, if thest
        try:
            self.df = pd.read_csv(filename)
        except:
            raise TypeError('cannot load the CSV file with file path %s, please make sure the file exists' % filename)

        # TODO: need to check if that accidentally drops the cancelled events
        self.df = self.df.dropna(subset=[self.RSVPER_NAMES, ])

        self.df[self.START_DATE] = pd.to_datetime(self.df[self.START_DATE], errors='coerce')
        self.df[self.START_DATE] = self.df[self.START_DATE].dt.date   # convert datetime to date (time is not necessary)
        self.df[self.RSVPER_NAMES] = self.df[self.RSVPER_NAMES].apply(lambda x: self.parse_rsvpers_string(x))

        self.df = self.df.sort_values(by=self.START_DATE, ascending=False)

        if debug:
            # Find the earliest date
            earliest_date = self.df[self.START_DATE].min()

            # Find the latest date
            latest_date = self.df[self.START_DATE].max()

            print(f'Earliest date: {earliest_date}')
            print(f'Latest date: {latest_date}')

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
