import pandas as pd
import datetime
from sesh_util import convert_date_str_to_obj, SeshEventTypeClassifier, SeshRSVPParser

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
CANCELLATION_REASON_REGEX = r'\([^)]+\)\s*'  # capture cancellation reason in parentheses
CANCELLED_EVENT_NAME_REGEX = rf'{SESH_CANCELLED_EVENT_TOKEN}\s+(?:{CANCELLATION_REASON_REGEX})?(?:\-\s*)?([^-]+)\s*'


class SeshData:
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
        self.df[RSVPER_NAMES] = self.df[RSVPER_NAMES].apply(lambda x: SeshRSVPParser.parse(x))
        self.df[EVENT_TYPE] = self.df[EVENT_NAME].apply(lambda x: SeshEventTypeClassifier.classify(x))
        self.df = self.df.sort_values(by=START_DATE, ascending=False)

        self.remove_canceled_event()

    def remove_canceled_event(self):
        """
        Identifying and removing both canceled events and their corresponding events within the previous week.
        """
        # Gather a list of canceled events based on a specific token in the event name
        cancelled_event_condition = self.df[EVENT_NAME].str.contains(SESH_CANCELLED_EVENT_TOKEN, case=False, na=False)
        cancelled_event_df = self.df[cancelled_event_condition]

        # Remove canceled events from the main DataFrame
        self.df = self.df[~cancelled_event_condition]

        indices_to_remove = []

        # Iterate over each canceled event to find related events within the last week
        for idx, cancelled_clinic_row in cancelled_event_df.iterrows():
            cancellation_date = cancelled_clinic_row[START_DATE]
            a_week_ago = cancellation_date - datetime.timedelta(days=7)
            event_type = cancelled_clinic_row[EVENT_TYPE]
            indices = self.df[
                (self.df[START_DATE] >= a_week_ago) &
                (self.df[START_DATE] < cancellation_date) &
                (self.df[EVENT_TYPE] == event_type)
                ].index.to_list()

            # Accumulate indices of related events to remove
            indices_to_remove.extend(indices)

        # Drop the identified rows from the DataFrame
        self.df.drop(indices_to_remove, inplace=True)
        self.df.reset_index(drop=True, inplace=True)

    def get_clinic_events(self):
        return self.df[self.df[EVENT_TYPE].str.contains('Clinic', case=False, na=False)]

    def get_event(self, event_type, event_date=None):
        if event_date is None:
            df = self.df[self.df[EVENT_TYPE] == event_type]
        else:
            df = self.df[(self.df[START_DATE] == event_date) & (self.df[EVENT_TYPE] == event_type)]

        if len(df) == 0:
            raise Exception(f'SeshData get_event error: cannot find event of type {event_type} on date {event_date}')

        return df.iloc[0]

    def get_latest_events(self, event_type, before_event_date=None, max_sessions=3):
        if before_event_date is None:
            before_event_date = datetime.date.today()
        elif isinstance(before_event_date, str):
            before_event_date = convert_date_str_to_obj(before_event_date)
        elif not isinstance(before_event_date, datetime.date):
            raise TypeError(f'event_date {before_event_date} needs to be of type(datetime.date)')

        df = self.df[
            (self.df[START_DATE] < before_event_date) &
            (self.df[EVENT_TYPE] == event_type)
            ].sort_values(by=START_DATE, ascending=False)

        # Get the date of the first and last sessions within the first max_sessions rows
        df = df.head(max_sessions)
        last_session_date = df.head(1)[START_DATE].iloc[0]
        first_session_date = df.tail(1)[START_DATE].iloc[0]

        df = df[
            (df[START_DATE] >= first_session_date) &
            (df[START_DATE] <= last_session_date)
            ]
        return df
