from sesh import EVENT_TYPE, START_DATE, RSVPER_NAMES
from sesh_util import BEG_CLINIC, ADV_BEG_CLINIC, INT_CLINIC, ADV_INT_CLINIC
import os, datetime


def get_day_of_week(date: datetime.date, abbreviate=True) -> str:
    """
        Args:
            date:
            abbreviate:
        Returns: string for day of week
        Example usage:
        day_of_week = get_day_of_week(date)
        print(f"The day of the week for {date} is {day_of_week}.")

    """
    if not abbreviate:
        # Get the day of the week (0=Monday, 6=Sunday)
        day_of_week = date.strftime("%A")
        return day_of_week
    else:
        # Get the 3-letter abbreviation of the day of the week
        day_of_week_abbr = date.strftime("%a")
        return day_of_week_abbr


def convert_event_type_to_desc(event_type: str) -> str:
    if event_type == BEG_CLINIC:
        event_desc = 'Beginner Clinic (2.0 to 2.5)'
    elif event_type == ADV_BEG_CLINIC:
        event_desc = 'Adv Beg Clinic (2.75 to 3.0)'
    elif event_type == INT_CLINIC:
        event_desc = 'Intermed Clinic (3.25)'
    elif event_type == ADV_INT_CLINIC:
        event_desc = 'Adv Intermed Clinic (3.50)'
    else:
        raise (f'unknown event_type: {event_type}')
    return event_desc


def coach_huddle_whosin(lottery_events, write_to_csv, append_to_file=True):
    write_mode = 'a' if append_to_file is True else 'w'
    if write_mode == 'w' and os.path.exists(write_to_csv):
        os.remove(write_to_csv)
    with open(write_to_csv, write_mode) as file:
        for idx, lottery_event in lottery_events.iterrows():
            event_type = lottery_event[EVENT_TYPE]
            event_date = lottery_event[START_DATE]
            event_day_of_week = get_day_of_week(event_date, abbreviate=True)
            event_desc = f'{event_day_of_week} {convert_event_type_to_desc(event_type)}'
            file.write(f"{event_date} {event_desc} - Who's In?\n")

        file.write(f"Body of the thread \n \
        :star:  Thread for coaches and assistants to chat about the upcoming session, who's in, the topic, etc. @coach/asst .\n")
        file.close()
