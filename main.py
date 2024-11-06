from sesh_util import convert_date_str_to_obj
from event import ClinicEventManager
from sesh import SeshData, RSVPER_NAMES, ATTENDEES, START_DATE, WAITLIST
from lottery import Lottery
from history import AttendanceHistory

if __name__ == '__main__':
    sesh_data = SeshData('test_data/test.csv')
    date_str = '2024-06-11'

    date = convert_date_str_to_obj(date_str)
    event_type = 'Intermediate Clinic'

    clinic_sessions = ClinicEventManager(sesh_data.df)
    clinic_session = clinic_sessions.get_event(event_date=date, event_type=event_type)
    clinic_sessions_by_level = clinic_sessions.get_latest_events(event_date=date, event_type=event_type)

    rsvper_names = clinic_session[RSVPER_NAMES].iloc[0]
    names = rsvper_names.get(ATTENDEES, []) + rsvper_names.get(WAITLIST, [])

    last_n_dates = clinic_sessions_by_level[START_DATE].to_list()
    attendance_history = AttendanceHistory(last_n_dates, clinic_sessions.df)
    print('names:', names)
    lottery = Lottery(attendance_df=attendance_history.get_small_df(names))
    winners = lottery.select_winners()
    print(lottery.priority_df)
    print('winners:', winners)
