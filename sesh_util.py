import re
from enum import Enum
from datetime import datetime


def convert_date_str_to_obj(date_str):
	# Convert to datetime object
	event_date_regex = "%Y-%m-%d"  # ex. ""2023-10-08" or "2024-10-22"

	date_obj = datetime.strptime(date_str, event_date_regex).date()
	return date_obj


CLINIC = 'clinic'
ADV_INT_CLINIC = 'Advanced Intermediate Clinic'
INT_CLINIC = 'Intermediate Clinic'
ADV_BEG_CLINIC = 'Advanced Beginner Clinic'
BEG_CLINIC = 'Beginner Clinic'
ROUNDROBIN = 'round robin'
BALL_MACHINE_SESSION = 'Ball Machine Session'
DUPR_MATCHES = 'DUPR Matches'
GETTING_STARTED = 'Getting Started'
OTHER = 'other'


class SeshEventTypeClassifier:
	@staticmethod
	def classify(event_name: str) -> str:
		if re.search(r'Advanced Intermediate Clinic', event_name, re.IGNORECASE):
			return ADV_INT_CLINIC
		elif re.search(r'Intermediate Clinic', event_name, re.IGNORECASE):
			return INT_CLINIC
		elif re.search(r'Advanced Beginner Clinic', event_name, re.IGNORECASE):
			return ADV_BEG_CLINIC
		elif re.search(r'Beginner Clinic', event_name, re.IGNORECASE):
			return BEG_CLINIC
		elif re.search(r'Round Robin - \d\.\d+ to \d\.\d+', event_name, re.IGNORECASE):
			return re.findall(r'Round Robin - \d\.\d+ to \d\.\d+', event_name, re.IGNORECASE)[0]
		elif re.search(r'DUPR Matches', event_name, re.IGNORECASE):
			return DUPR_MATCHES
		elif re.search(r'Getting Started', event_name, re.IGNORECASE):
			return GETTING_STARTED
		elif re.search(r'Ball Machine Session\s*\([0-9.,\s]+\)', event_name, re.IGNORECASE):
			return BALL_MACHINE_SESSION
		else:
			return OTHER


class SeshRSVPParser:
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

	@staticmethod
	def parse(rsvpers_str: str) -> dict:
		"""
		Parse a string containing lists of attendees under different headers.
		Returns a dictionary with headers as keys and lists of names as values.
		:param rsvpers_str: Input string in the format "Header1: name1,name2,...,Header2: name1,name2,..."
		:return: dict: Dictionary with headers as keys and lists of names as values
		"""

		result = {}
		sections = re.findall(SeshRSVPParser.section_pattern, rsvpers_str, flags=re.VERBOSE)

		# Step 2: Find all matches using the pattern
		for section_header, section_value in sections:
			cleaned_section_value = section_value.strip(' ,"')
			names = re.split(r'\s*,\s*', cleaned_section_value)
			names = [
				re.sub(SeshRSVPParser.nickname_pattern, ' ', name.strip())
				for name in names if len(name) > 0 and not name.isspace()
			]
			result[section_header] = names
		return result
