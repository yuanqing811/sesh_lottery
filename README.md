# Lottery Program

A Python-based tool for managing and conducting a lottery system for event attendees,
enabling priority-based selection and efficient session handling.

---

## Background

At popular events, demand for event slots often exceeds availability.
To ensure fairness, we prefer a lottery system over a first-come-first-serve approach
for event registration, blending random selection with attendance priority.

Currently, we use Discord and Sesh Bot for managing events, but since Sesh lacks lottery support,
we manually conduct lotteries via a Excel spreadsheet, which is a time-consuming process requires

1. Manually downloading the event attendance data in the form a csv file,
2. Manually updating the Excel spreadsheet with RSVP information,
3. Manually running the Excel macro to perform lottery.

This project aims to replace that manual process 2 and 3 with a Python program
to automate participant selection, This will streamline and simplify weekly lottery management.

## Features

- **Event and Attendance Management**: Track attendees and their history.
- **Lottery System**: Select attendees and waitlist based on defined priorities.

## Prerequisites
   Ensure you have the following installed on your system: Python 3.9 or later

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yuanqing811/PAPC_lottery.git
   cd PAPC_lottery
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
## Configuration
   This program uses a YAML file to define the parameters for performing 
   lotteries for all the clinic. An example YAML file structure is provided below:

**Example YAML File**
```bash
# clinic.yaml
csv_filename: 'test_data/events_1059745565136654406_2024-11-14.csv'
output_dir: 'output'
exclude_from_lottery: []
start_date: 2024-11-18
recurring_interval_in_days: 7 # weekly

events:
  Clinic-B:
    lottery:
      order: 0
      max_attendee_count: 16
    attendance_history:
      num_past_sessions: 3

  Clinic-AB:
    lottery:
      order: 1
      max_attendee_count: 16
    attendance_history:
      num_past_sessions: 3

  Clinic-I:
    lottery:
      order: 3
      max_attendee_count: 16
    attendance_history:
      num_past_sessions: 3

  Clinic-AI:
    lottery:
      order: 2
      max_attendee_count: 16
    attendance_history:
      num_past_sessions: 3
```
## Usage

1. **Run Lottery**: Conduct weekly clinic lottery using `clinic_lottery.py`.
   ```bash
   python clinic_lottery.py <yaml_filename>
   ```
   **Example Command**
   ```bash
   python clinic_lottery.py weekly_clinic_lottery.yaml 
   ```
   This command reads the csv file specified in `weekly_clinic_lottery.yaml`
   and processes it to retrieve past clinic attendance and lottery information,
   chooses future clinic attendees and waitlist based on that information.

## Example Workflow
1. Download the .csv file from Discord Sesh.
2. Prepare the configuration file (e.g., `weekly_clinic_lottery.yaml` ).
   - Update the .csv file name to the latest.
   - Adjust the lottery week start date. Leave empty to choose next Monday.
   - You can also adjust the order in which clinic lotteries are run.
   - You can adjust the maximum number of attendees for each clinic.
2. Run the program with the configuration file as an argument.
3. The program will: 
   - Read the configuration details from the YAML file.
   - Parse the csv file from the specified `csv_filename`.
   - Generates the lottery results to the specified `output_dir`.

## Testing

Run tests:
```bash
python test.py
```

--- 

