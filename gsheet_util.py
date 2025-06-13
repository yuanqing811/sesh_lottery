import pandas as pd
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials


def move_file_to_folder(
        file_id, folder_id,
        credentials_path="config/papclottery-aabf0d892e93.json"
    ):

    # Set up Drive API
    scopes = ['https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
    drive_service = build('drive', 'v3', credentials=creds)

    # Retrieve existing parents
    file = drive_service.files().get(fileId=file_id, fields='parents').execute()
    previous_parents = ",".join(file.get('parents'))

    # Move the file to the new folder
    file = drive_service.files().update(
        fileId=file_id,
        addParents=folder_id,
        removeParents=previous_parents,
        fields='id, parents'
    ).execute()

    print(f"Moved file {file_id} to folder {folder_id}")


def get_or_create_spreadsheet(client, spreadsheet_name):
    try:
        spreadsheet = client.open(spreadsheet_name)
        print(f"Spreadsheet '{spreadsheet_name}' found.")
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"Spreadsheet '{spreadsheet_name}' not found. Creating...")
        spreadsheet = client.create(spreadsheet_name)
        print(f"Spreadsheet '{spreadsheet_name}' created.")

        # Create a new sheet before deleting the default one
        spreadsheet.add_worksheet(title='Data', rows=1000, cols=26)
        
        try:
            # Now we can safely delete the default sheet
            default_worksheet = spreadsheet.sheet1
            spreadsheet.del_worksheet(default_worksheet)
            print("Default sheet deleted successfully.")
        except Exception as e:
            print(f"Warning: Could not delete default sheet: {e}")
            print("Continuing with default sheet...")

    return spreadsheet


def get_or_create_worksheet(spreadsheet, worksheet_title, rows=1000, cols=26):
    try:
        worksheet = spreadsheet.worksheet(worksheet_title)
        print(f"Worksheet '{worksheet_title}' found.")
    except gspread.exceptions.WorksheetNotFound:
        print(f"Worksheet '{worksheet_title}' not found. Creating...")
        worksheet = spreadsheet.add_worksheet(title=worksheet_title, rows=str(rows), cols=str(cols))
        print(f"Worksheet '{worksheet_title}' created.")
    return worksheet


def read_spreadsheet_to_df(
    spreadsheet_name,
    sheet_name='Sheet1',
    credentials_path="config/papclottery-aabf0d892e93.json"
):
    """
    Reads a Google Sheet worksheet into a pandas DataFrame.

    Args:
        spreadsheet_name (str): The name of the Google Spreadsheet.
        sheet_name (str): The name of the worksheet/tab within the spreadsheet.
        credentials_path (str): Path to the service account credentials JSON file.

    Returns:
        pd.DataFrame: The loaded DataFrame.
    """
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    try:
        credentials = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
        client = gspread.authorize(credentials)

        spreadsheet = client.open(spreadsheet_name)
        worksheet = spreadsheet.worksheet(sheet_name)

        df = get_as_dataframe(worksheet, evaluate_formulas=True, header=0)
        return df.dropna(how="all")  # Drop empty rows
    except Exception as e:
        print(f"Error reading spreadsheet: {e}")
        raise


def write_df_to_google_sheet(
        df, sheet_name,
        worksheet_title='Sheet1',
        credentials_path='config/papclottery-aabf0d892e93.json'):
    """
    Writes a pandas DataFrame to a Google Sheet

    Args:
        df (pd.DataFrame): The DataFrame to write.
        sheet_name (str): The name of the Google Sheet (not the file ID).
        worksheet_title (str): The title of the sheet tab (default is 'Sheet1').
        credentials_path (str): Path to your service account JSON credentials.

    Returns:

    """
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
    client = gspread.authorize(credentials)

    # Open the spreadsheet and worksheet
    # 1️⃣ Create the spreadsheet
    sheet = get_or_create_spreadsheet(client, sheet_name)
    worksheet = get_or_create_worksheet(sheet, worksheet_title)

    # Clear existing content
    worksheet.clear()

    # Write DataFrame to sheet
    set_with_dataframe(worksheet, df)
    print(f"Data written to {sheet_name} > {worksheet_title}")

    # 2️⃣ Move it to folder
    spreadsheet_id = sheet.id
    move_file_to_folder(
        file_id=spreadsheet_id,
        folder_id='1YoXHGt9cj9121Sk16N0z_efpb75Xh0tC',  # The target folder ID from Drive URL
    )


def append_df_to_google_sheet(
        df, sheet_name,
        worksheet_title='Sheet1',
        credentials_path='config/papclottery-aabf0d892e93.json',
        include_column_header=True):
    """
    Appends a DataFrame to the next available row of a Google Sheet worksheet.

    Args:
        df (pd.DataFrame): DataFrame to append.
        sheet_name (str): Name of the spreadsheet.
        worksheet_title (str): Tab name of the worksheet.
        credentials_path (str): Path to credentials.json file.
        include_column_header (bool): Whether to include column headers.
    """

    # Auth
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
    client = gspread.authorize(creds)

    # Open sheet and worksheet
    sheet = get_or_create_spreadsheet(client, sheet_name)
    worksheet = get_or_create_worksheet(sheet, worksheet_title)

    # Find next empty row
    values = worksheet.get_all_values()
    next_row = len(values) + 1 if values else 1

    # Append DataFrame
    set_with_dataframe(worksheet, df, row=next_row, include_column_header=include_column_header, resize=False)
    print(f"Appended DataFrame at row {next_row} of '{sheet_name} > {worksheet_title}'")


def append_df_with_title_to_google_sheet(
    df,
    section_title,
    sheet_name,
    worksheet_title='Sheet1',
    credentials_path='config/papclottery-aabf0d892e93.json',
    include_column_header=True
):
    """
    Appends a section title and DataFrame to the next available row in a Google Sheet worksheet.

    Args:
        df (pd.DataFrame): The DataFrame to append.
        section_title (str): A title to insert above the DataFrame.
        sheet_name (str): Name of the spreadsheet.
        worksheet_title (str): Tab name of the worksheet.
        credentials_path (str): Path to credentials.json file.
        include_column_header (bool): Whether to include column headers.
    """
    # Auth
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
    client = gspread.authorize(creds)

    # Open sheet and worksheet
    sheet = client.open(sheet_name)
    worksheet = sheet.worksheet(worksheet_title)

    # Find next empty row
    values = worksheet.get_all_values()
    next_row = len(values) + 1 if values else 1

    # Insert section title
    worksheet.update_cell(next_row, 1, section_title)
    next_row += 1

    # Append DataFrame
    set_with_dataframe(worksheet, df, row=next_row, include_column_header=include_column_header, resize=False)
    print(f"Appended section '{section_title}' at row {next_row - 1} of '{sheet_name} > {worksheet_title}'")
