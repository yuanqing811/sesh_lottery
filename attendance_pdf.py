from fpdf import FPDF


class AttendancePDF(FPDF):
    def header(self):
        # Title dynamically set in the main function
        pass

    def set_dynamic_header(self, date, day, clinic_level):
        """
        Set the dynamic header with date, day, and clinic level.
        """
        self.set_font('Arial', 'B', 12)
        title = f"{date} {day} {clinic_level} Attendance List"
        self.cell(0, 10, title, align='C', ln=True)
        self.ln(10)

    def add_table(self, data, x, y, col_widths, headers, section_title):
        """
        Add a table at a specific position with a section title.

        Args:
            data (list): List of rows (each row is a list of strings).
            x (float): Starting x-coordinate.
            y (float): Starting y-coordinate.
            col_widths (list): List of column widths.
            headers (list): List of column headers.
            section_title (str): Title for the section.
        """
        self.set_xy(x, y)
        line_height = 6  # Adjust for smaller font

        # Section Title
        self.set_font('Arial', 'B', 8)
        self.cell(0, line_height, section_title, ln=True)
        self.ln(2)

        # Table Header
        self.set_font('Arial', 'B', 8)
        for i, header in enumerate(headers):
            self.cell(col_widths[i], line_height, header, border=1, align="C")
        self.ln(line_height)

        # Table Body
        self.set_font('Arial', '', 8)
        for row in data:
            for i, cell in enumerate(row):
                self.cell(col_widths[i], line_height, str(cell), border=1, align="L")
            self.ln(line_height)

    def add_right_column_list(self, x, y, width, info):
        """
        Add the right column content as a list.

        Args:
            x (float): Starting x-coordinate.
            y (float): Starting y-coordinate.
            width (float): Width of the column.
            info (dict): Grouped information to display.
        """
        self.set_xy(x, y)
        line_height = 5  # Line height for list items
        self.set_font('Arial', 'B', 8)

        for section, items in info.items():
            # Section header
            self.set_xy(x, self.get_y())
            self.cell(width, line_height, section, ln=True)
            self.set_font('Arial', '', 8)  # Smaller font for list items
            for item in items:
                self.set_xy(x, self.get_y())
                self.cell(width, line_height, f"  - {item}", ln=True)
            self.ln(2)  # Space between sections
            self.set_font('Arial', 'B', 8)  # Reset to bold for the next section


def generate_pdf(attendees, waitlist, date, day, clinic_level, right_column_data, filename="output.pdf"):
    pdf = AttendancePDF()
    pdf.add_page()

    # Page dimensions
    page_width = pdf.w
    margin = pdf.l_margin
    column_spacing = 5  # Space between columns
    left_column_width = (2/3) * (page_width - 2 * margin)
    right_column_width = (1/3) * (page_width - 2 * margin)

    # Set the dynamic header
    pdf.set_dynamic_header(date, day, clinic_level)

    # Y-coordinate for both sections in the left column
    current_y = pdf.get_y()

    # Prepare data for the attendees section
    headers = ["No.", "Name", "Present", "Comments"]
    col_widths = [left_column_width * 0.1, left_column_width * 0.5, left_column_width * 0.2, left_column_width * 0.2]
    attendees_data = [[i + 1, name, "", ""] for i, name in enumerate(attendees)]

    # Add the attendees section in the left column
    pdf.add_table(data=attendees_data, x=margin, y=current_y, col_widths=col_widths, headers=headers, section_title="Attendees")

    # Save the initial Y-coordinate for the right column alignment
    right_column_y = current_y

    # Update Y-coordinate for the waitlist section
    current_y = pdf.get_y() + 5  # Add some spacing

    # Prepare data for the waitlist section
    waitlist_data = [[i + 1, name, "", ""] for i, name in enumerate(waitlist)]

    # Add the waitlist section in the left column
    pdf.add_table(data=waitlist_data, x=margin, y=current_y, col_widths=col_widths, headers=headers, section_title="Waitlist")

    # Add the right column as a list, aligned with the top of the attendees table
    pdf.add_right_column_list(
        x=margin + left_column_width + column_spacing,  # Position to the right of the left column
        y=right_column_y,  # Align with the top of the attendees table
        width=right_column_width,
        info=right_column_data
    )

    # Output to file
    pdf.output(filename)


# Example usage
if __name__ == "__main__":
    attendees = [
        "Vanessa Lemahieu", "Cindy Chen Tim Wong", "Vae Sun", "Cindy Campbell",
        "Wendy Kandasamy", "Steve Lawrence Paige Kolze", "Priya 'Power' Balachandran John Wang",
        "Monica Chan Joseph Afong", "Wycee Reshko Jeanne Hsu", "Jeffrey Chu Billy Chow"
    ]

    waitlist = [
        "Emily Yuen", "Brad Bender", "Carrie Anderson", "Gabi Gayer",
        "Sam Bunger", "Dione Chen", "Lusi Chien", "Mark Fan"
    ]

    # Parameters for the attendance list
    date = "2024-11-20"
    day = "Wednesday"
    clinic_level = "Advanced Beginners"

    # Grouped information for the right column
    right_column_data = {
        "Head Coach": ["Vanessa Lemahieu"],
        "Assistant Coaches": ["Cindy Chen", "Tim Wong"],
        "Clinic Topics Covered": ["Safety", "Footwork", "Game Point Analysis"],
        "Notes for Attendance": ["Mark 'NS' for No Show", "24 attendees max per clinic"]
    }

    generate_pdf(attendees, waitlist, date, day, clinic_level, right_column_data, filename="output/attendance_list.pdf")
