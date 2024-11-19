import os

import os


def generate_unique_filename(base_filename):
    """
    Generate a unique filename by appending an index in parentheses if the file already exists.

    Args:
        base_filename (str): The full path of the desired filename, including the directory.

    Returns:
        str: A unique filename that does not overwrite an existing file.
    """
    # Separate the directory and filename
    directory, filename = os.path.split(base_filename)
    if not directory:
        directory = "."  # Default to current directory if no directory is specified

    # Extract the file name and extension
    name, ext = os.path.splitext(filename)

    # Check if the file already exists
    new_filename = filename
    counter = 1
    while os.path.exists(os.path.join(directory, new_filename)):
        new_filename = f"{name}({counter}){ext}"
        counter += 1

    return os.path.join(directory, new_filename)


