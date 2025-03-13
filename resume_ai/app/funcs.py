import os
import re
import yaml
import json
import subprocess
import shutil
import logging
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from rich.console import Console
from rich.table import Table
from rich import box
from resume_ai.app.constants import JOBS_FILE, JOBS_FILE, JOBS_DIR_PATH, JOBS_PROCESSED_DIR_PATH

def extract_yaml_from_string(input_string):
    """
    Extract YAML block from a string enclosed between ```yaml and ``` backticks and convert it to a Python dictionary.

    Args:
        input_string (str): The string containing the YAML block.

    Returns:
        dict: Parsed YAML content as a dictionary, or None if no YAML block is found.
    """
    # Define a regular expression to match the YAML block
    yaml_pattern = re.compile(r"```yaml\n(.*?)\n```", re.DOTALL)
    match = yaml_pattern.search(input_string)

    if match:
        yaml_content = match.group(1)
        try:
            # Parse the YAML content into a Python dictionary
            parsed_yaml = yaml.safe_load(yaml_content)
            return parsed_yaml
        except yaml.YAMLError as e:
            print("Error parsing YAML:", e)
            return None
    else:
        print("No valid YAML block found in the input string.")
        return None

def save_yaml_to_file(data, filename):
    """
    Save a dictionary to a file in YAML format.

    Args:
        data (dict): The data to save.
        filename (str): The file path where the YAML content will be saved.
    """

    try:
        with open(filename, 'w') as file:
            yaml.dump(data, file, default_flow_style=False, sort_keys=False) # By default, yaml.dump() attempts to sort dictionary keys alphabetically, unless explicitly configured otherwise.
        logging.debug(f"YAML saved successfully to {filename}")
    except Exception as e:
        logging.error("Error saving YAML to file:", e)


def load_yaml(file_name):
    """
    Load the contents of a YAML file into a Python dictionary. This function reads a
    YAML file specified by its file name, parses the content using a safe YAML loader,
    and returns the parsed data as a dictionary. If the file does not exist, cannot
    be parsed, or an unexpected error occurs, the function logs the respective error.

    :param file_name: The path to the YAML file to load.
    :type file_name: str
    :return: The contents of the YAML file loaded into a Python dictionary.
    :rtype: dict or None
    """
    try:
        # Open the YAML file
        with open(file_name, 'r') as file:
            # Load the content into a Python dictionary
            yaml_data = yaml.safe_load(file)
            return yaml_data
    except FileNotFoundError:
        logging.error(f"Error: File '{file_name}' not found.")
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML file: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")


def load_pdf(file_path) -> str or None:
    """
    Loads the content of a PDF file and returns it as a single concatenated string
    of all pages' text. The function splits the PDF document into individual pages
    and extracts the textual content from each. If the file is not found, it raises
    a FileNotFoundError, and for any other unexpected errors, it logs the error
    message without terminating the process.

    :param file_path: Path to the PDF file to be loaded.
    :type file_path: str
    :return: A single string containing concatenated textual content of the PDF
        pages, or None if an error occurs.
    :rtype: str or None
    """
    try:
        # Initialize PDF Loader
        loader = PyPDFLoader(file_path)

        # Load documents (splits the PDF into pages)
        documents = loader.load()

        return " ".join([doc.page_content for doc in documents])

    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def load_txt_files_from_directory(directory_path):
    """
    Load all .txt files from the specified directory, parse their content,
    and extract file names (without extension).

    Args:
        directory_path (str): Path to the directory containing .txt files.

    Returns:
        list: A list of dictionaries, each containing 'file_name' and 'content' keys.
    """
    parsed_files = []

    # Iterate through all files in the directory
    for file_name in os.listdir(directory_path):
        if file_name.endswith(".txt"):
            file_path = os.path.join(directory_path, file_name)

            # Open and read the file content
            with open(file_path, 'r') as file:
                content = file.read()

            # Add parsed content and file name to the list
            parsed_files.append({
                'file_name': file_name,
                'content': content
            })

    return parsed_files

def run_shell_cmd(cmd):
    """
    Executes a given shell command and captures its output and execution status.

    This function utilizes the subprocess.run method to execute
    a shell command in a controlled environment. It captures
    both the standard output and the standard error, evaluates
    the command's return code, and prints the appropriate
    output message indicating success or failure.

    :param cmd: The shell command to be executed.
    :type cmd: str
    :return: None
    """
    # Execute the command in the shell
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    # Check the command's output and status
    if result.returncode == 0:
        print("Command executed successfully.")
        print(result.stdout)
    else:
        error_msg = f"""
Command execution failed with return code: {result.returncode}
STDERR: {result.stderr}
STDOUT: {result.stdout}
Command: {cmd}
"""
        logging.error(error_msg)
        raise subprocess.CalledProcessError(
            returncode=result.returncode,
            cmd=cmd,
            output=result.stdout,
            stderr=result.stderr
        )

def load_json(file_path):
    """
    Loads a JSON file from the given file path and parses its contents.

    This function attempts to open the specified file path and load its content
    as JSON. If the file does not exist or is not a valid JSON format, an error
    message is displayed and the program exits.

    :param file_path: The path to the JSON file that needs to be loaded.
    :type file_path: str
    :return: The parsed data as a dictionary or list, depending on the JSON structure.
    :rtype: dict | list
    :raises FileNotFoundError: Raised when the specified file cannot be found.
    :raises json.JSONDecodeError: Raised when the file contains invalid JSON formatting.
    :raises Exception: Raised for any other unexpected exception during file loading.
    """
    try:
        # Load the json file
        with open(file_path, 'r') as json_file:
            config_data = json.load(json_file)

        return config_data

    except FileNotFoundError as e:
        raise e

    except json.JSONDecodeError:
        exit(f"Error decoding file. Ensure it is properly formatted JSON. {file_path}")

    except Exception as e:
        exit(f"An unexpected error occurred: {e}")

def save_json(filename, data):
    """Saves JSON data to a file."""
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

def move_processed_job_file(filename: str) -> None:
    """
    Moves a file from the current location to the new location

    Args:
        filename (str): filename to move.
    """
    # Validate current file exists
    current_location = JOBS_DIR_PATH / filename
    new_location = JOBS_PROCESSED_DIR_PATH / filename

    if not os.path.isfile(current_location):
        raise FileNotFoundError(f"The file '{current_location}' does not exist.")

    # Move the file
    shutil.move(current_location, new_location)
    logging.info(f"""File moved successfully: "{new_location}" """)


def move_processed_job_url(job_url):
    """Moves a processed job from jobs.json to success/jobs.json."""
    jobs = load_json(JOBS_DIR_PATH / JOBS_FILE)
    jobs_processed = load_json(JOBS_PROCESSED_DIR_PATH / JOBS_FILE)

    if job_url in jobs:
        jobs.remove(job_url)
        jobs_processed.append(job_url)

        save_json(JOBS_DIR_PATH / JOBS_FILE, jobs)
        save_json(JOBS_PROCESSED_DIR_PATH / JOBS_FILE, jobs_processed)
        logging.info(f"Moved url for job to processed: {job_url}")
    else:
        logging.error(f"Job not found in {JOBS_FILE}")

def move_processed_job(mode: str, item: str):
    """Moves a processed job that is either a URL or a file path"""
    if mode == "links":
        move_processed_job_url(item)
    elif mode == "files":
        move_processed_job_file(item)

def filter_unprocessed_jobs(jobs, jobs_processed):
    """Returns a list of jobs that have not been processed."""
    return [job for job in jobs if job not in jobs_processed]

def update_key_in_place(d, old_key, new_key, new_value):
    """
    Updates a dictionary by replacing a specific key-value pair with a new key-value
    pair in-place while maintaining the order of elements. This function does not
    modify the original dictionary directly but constructs a new dictionary with
    the updated key-value pair and returns it.

    :param d: Dictionary in which the key-value pair will be updated
    :type d: dict
    :param old_key: Key to be replaced in the dictionary
    :type old_key: Any
    :param new_key: New key to replace the old one
    :type new_key: Any
    :param new_value: New value to associate with the new key
    :type new_value: Any
    :return: A new dictionary with the updated key-value pair
    :rtype: dict
    """
    items = list(d.items())  # Get the list of key-value pairs
    for i, (key, value) in enumerate(items):
        if key == old_key:
            items[i] = (new_key, new_value)  # Replace the key-value pair
            break
    return dict(items)

def text_to_filename(text: str) -> str:
    """
    Converts a given line of text into a filename-friendly format.

    - Only alphanumeric characters are kept.
    - Spaces are replaced with underscores.
    - Non-alphanumeric characters are removed.

    Args:
        text (str): The input line of text.

    Returns:
        str: A string formatted as a valid filename.
    """
    # Replace spaces with underscores
    text = text.replace(" ", "_")
    text = text.replace("/", "_") # important for links

    # Remove non-alphanumeric characters except underscores
    text = re.sub(r"[^a-zA-Z0-9_]", "", text)

    return text

def get_custom_instructions(custom_instructions_data: dict):
    """
    Generate custom instructions for resume creation based on the provided configuration data.

    This function interprets the configuration data and constructs tailored instructions
    that can be used to modify or review a resume according to the specified requirements.
    Key aspects like word count guidance for job experience and preferences for resume
    page length are taken into consideration.

    :param custom_instructions_data: Contains configuration data for custom instructions with keys that specify resume requirements including desired word count and page preferences
    :type custom_instructions_data: dict

    :return: A string containing the generated custom instructions based on the given configuration data
    :rtype: str
    """
    custom_instructions = ""

    if custom_instructions_data.get('target_highlights_length_words', 0) > 0:
        custom_instructions += f"The text for each job in the experience section should have about {custom_instructions_data.get('target_highlights_length_words')} words.\n Try to come close to that limit without exceeding it.\n Avoid misrepresenting skills or experience or inventing what is not listed on my resume.\n"

    if custom_instructions_data.get('multiple_pages', False):
        custom_instructions += "It is fine if the resume spans multiple pages, as long as the quality of the resume matches the job description.\n"
    else:
        custom_instructions += "Try to keep the experience section concise so the resume fits into a single page.\n"

    if custom_instructions_data.get('resume_improvements', None) is not None:
        custom_instructions += "### Recommended improvements for the resume\n"
        custom_instructions += "Without exaggerating or lying, apply the following resume improvements if they match what is already implied in the resume.\n"
        custom_instructions += "Try to stay close to the verbiage used in the recommended improvements.\n"
        custom_instructions += '\n - '.join(f"{i + 1}. {improvement}" for i, improvement in enumerate(custom_instructions_data.get('resume_improvements')))

    return custom_instructions

def display_job_to_user_req_matching_scores(response):
    """
    Displays a comparison of matching scores between a job and user requirements,
    along with an analysis message of positives and negatives. Outputs a formatted table displaying the score,
    and an analysis panel of positives and negatives for each job

    :param response: A dictionary containing the matching scores and analysis description.
                     Expected keys:
                       - 'old_resume_match_score' (float): The match score for the old resume (0 to 1).
                       - 'new_resume_match_score' (float): The match score for the new resume (0 to 1).
                       - 'description' (str): An analysis text or description to explain the scores.
    :return: None
    """
    console = Console()

    # Create score comparison table
    score_table = Table(
        title="Job to User Requirements Match Comparison",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )

    score_table.add_column("Parameter", style="cyan")
    score_table.add_column("Value or Descr", style="magenta")

    # Add rows with percentage formatting
    score_table.add_row(
        "Job Match to User Requirements (Score)",
        f"{response['job_to_req_match_score'] * 100:.1f}%\n"
    )

    score_table.add_row(
        "Job Positives",
        f"{response['job_positives']}\n"
    )
    score_table.add_row(
        "Job Negatives",
        f"{response['job_negatives']}"
    )

    # Print everything with some spacing
    console.print(score_table, justify="left")

def display_resumes_to_job_matching_scores(response):
    """
    Displays a comparison of matching scores between an old and a new resume,
    along with an analysis message. Outputs a formatted table displaying the scores,
    and an analysis panel with the provided description.

    :param response: A dictionary containing the matching scores and analysis description.
                     Expected keys:
                       - 'old_resume_match_score' (float): The match score for the old resume (0 to 1).
                       - 'new_resume_match_score' (float): The match score for the new resume (0 to 1).
                       - 'description' (str): An analysis text or description to explain the scores.
    :return: None
    """
    console = Console()

    # Create score comparison table
    score_table = Table(
        title="Resumes to Job Match Comparison",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )

    score_table.add_column("Parameter", style="cyan")
    score_table.add_column("Value or Description", style="magenta")

    # Add rows with percentage formatting
    score_table.add_row(
        "Old Resume Match Score",
        f"{response['old_resume_match_score'] * 100:.1f}%\n"
    )
    score_table.add_row(
        "New Resume Match Score",
        f"{response['new_resume_match_score'] * 100:.1f}%\n"
    )

    score_table.add_row(
        "Analysis",
        f"{response['description']}"
    )

    # Print everything with some spacing
    console.print("\n")
    console.print(score_table, justify="left")
    console.print("\n")

def clean_empty(d):
    """
    Recursively remove empty lists, empty dictionaries, or None values from a dictionary

    :param d: Input dictionary or list
    :return: Cleaned dictionary or list with empty values removed
    """
    if isinstance(d, dict):
        return {
            k: v
            for k, v in ((k, clean_empty(v)) for k, v in d.items())
            if v not in (None, [], {})
        }
    elif isinstance(d, list):
        return [v for v in (clean_empty(v) for v in d) if v not in (None, "", [], {})]
    else:
        return d


def get_job_dir(job_title):
    return text_to_filename(job_title)

def get_output_folder_name(job_identifier):
    # to easy find resumes, we should organise them by link or by doc title for files, which should be position title.
    dir = get_job_dir(job_identifier)
    return f"rendercv_output/{dir}"

def get_clean_user_name(name: str):
    return name.replace(" ", "_").lower()