# the purpose of this script is to test if I can add event participants to the list of attendees

# I would like to write a script that automates scheduled data download like the event csv file
# Write scripts that automatically import the exported CSV files into your database.
# 1. Scheduled Exports:
# Set up a schedule to export data from Sesh Bot at regular intervals.
# 2. Automated Import Scripts:
# Write scripts that automatically import the exported CSV files into your database.
# identify the chrome session

def chunk_list(users, chunk_size=5):
    return [users[i:i + chunk_size] for i in range(0, len(users), chunk_size)]
