# PAPC Lottery Program

A Python-based tool for managing and conducting a lottery system for event attendees,
enabling priority-based selection and efficient session handling.

---

## Background

At the Palo Alto Pickleball Club, demand for event slots often exceeds availability.
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
- **Lottery System**: Select attendees based on defined priorities.

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

## Usage

1. **Event Setup**: Define events in `event.py`.
2. **Run Lottery**: Initialize and conduct a lottery using `lottery.py`.
3. **Session Management**: Use `sesh.py` and `sesh_util.py` for session handling.

## Files

- **`event.py`**: Manages event creation and attendee records.
- **`lottery.py`**: Main lottery logic.
- **`sesh.py`** & **`sesh_util.py`**: Session utilities.
- **`test.py`**: Unit tests for functionality validation.

## Testing

Run tests:
```bash
python test.py
```

--- 

