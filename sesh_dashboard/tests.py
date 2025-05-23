import yaml
from sesh_dashboard import SeshDashboardEvent


# Function to load YAML file
def load_yaml(file_path):
    with open(file_path, 'r') as file:
        data = yaml.safe_load(file)
    return data


# Example function to extract event data
def get_event_data(events, event_name):
    # Check if the event exists
    if event_name in events:
        event = events[event_name]
        return event
    else:
        raise f"Event '{event_name}' not found."


if __name__ == '__main__':
    events = load_yaml('../test_data/dash_test.yaml')
    event = get_event_data(events, "Qing's Test Event # 2")
    server_id = event['server_id']
    event_id = event['event_id']
    lottery = event['Lottery']
    attendee = event['Attendee']

    sesh_event_add_attendees = SeshDashboardEvent(server_id=server_id)
    sesh_event_add_attendees.add_users_to_list(event_id=event_id,
                                               list_name='Lottery',
                                               users=lottery)
