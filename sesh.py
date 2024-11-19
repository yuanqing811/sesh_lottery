import pandas as pd
import datetime
import logging
from sesh_util import convert_date_str_to_obj, SeshEventTypeClassifier, SeshRSVPParser
from logging_config import log_dataframe_info

# defining string constants
START_DATE = 'start date'
END_DATE = 'end date'
EVENT_NAME = 'name'
EVENT_TYPE = 'type'
EVENT_STATUS = 'status'
RSVPER_NAMES = 'rsvpers'
LOTTERY = 'Lottery'
ATTENDEES = 'Attendees'
WAITLIST = 'Attendees Waitlist'
RSVPER_LINK = 'rsvper_link'
EDIT_LINK = 'edit_link'
DISCORD_LINK = 'discord_link'
CHANNEL = 'channel'
AUTHOR = 'author'
SESH_CLINIC_EVENT_TOKEN = r'clinic'
SESH_RR_EVENT_TOKEN = 'round robin'
SESH_CANCELLED_EVENT_TOKEN = r'CANCELLED'

# defining regex
CANCELLATION_REASON_REGEX = r'\([^)]+\)\s*'  # capture cancellation reason in parentheses
CANCELLED_EVENT_NAME_REGEX = rf'{SESH_CANCELLED_EVENT_TOKEN}\s+(?:{CANCELLATION_REASON_REGEX})?(?:\-\s*)?([^-]+)\s*'


class SeshData:
    def __init__(self, filename: str) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        if not filename.endswith('.csv'):
            raise Exception('incorrect file type, please enter a csv filename that ends with .csv')

        self.logger.info(f'Reading from {filename}')
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
        self.logger.info(f'Finished loading event data from .csv file into a Dataframe')
        self.logger.info("Removing columns 'channel', 'author', 'rsvper_link', 'edit_link', 'discord_link' which are not used in lottery")
        self.df.drop([RSVPER_LINK, EDIT_LINK, DISCORD_LINK, CHANNEL, AUTHOR], axis=1, inplace=True)
        log_dataframe_info(self.df)
        self.logger.info(f'Converting event dates from string to datetime.date objects')
        self.df[START_DATE] = pd.to_datetime(self.df[START_DATE], errors='coerce')
        self.df[START_DATE] = self.df[START_DATE].dt.date   # convert datetime to date (time is not necessary)

        self.logger.info(f'Parsing Rsvper_names string and convert it into a dictionary')
        self.df[RSVPER_NAMES] = self.df[RSVPER_NAMES].apply(lambda x: SeshRSVPParser.parse(x))

        self.logger.info(f'Identifying the types of events based on event name')
        self.df[EVENT_TYPE] = self.df[EVENT_NAME].apply(lambda x: SeshEventTypeClassifier.classify(x))

        self.logger.info(f'Sort events in descending order based on dates')
        self.df = self.df.sort_values(by=START_DATE, ascending=False)
        log_dataframe_info(self.df)

    @staticmethod
    def remove_canceled_event(df: pd.DataFrame) -> pd.DataFrame:
        """
        Identifying and removing both canceled events and their corresponding events within the previous week.
        """
        # Gather a list of canceled events based on a specific token in the event name
        cancelled_event_condition = df[EVENT_NAME].str.contains(SESH_CANCELLED_EVENT_TOKEN, case=False, na=False)
        cancelled_event_df = df[cancelled_event_condition]
        cancelled_event_indices = cancelled_event_df.index.tolist()
        # Remove canceled events from the main DataFrame
        df.drop(index=cancelled_event_indices, inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    def get_clinic_events(self) -> pd.DataFrame:
        df = self.df[self.df[EVENT_TYPE].str.contains('Clinic', case=False, na=False)]
        # Expand the 'rsvper_names' column into separate columns with a nested structure
        df_expanded = df[RSVPER_NAMES].apply(pd.Series)
        df_expanded.columns = pd.MultiIndex.from_product([[RSVPER_NAMES], df_expanded.columns])
        df.drop(columns=[RSVPER_NAMES])

        df = pd.concat([df, df_expanded], axis=1)
        return df

    def get_latest_events(self,
                          event_type: str,
                          before_event_date=None,
                          max_sessions=3) -> pd.DataFrame:
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
