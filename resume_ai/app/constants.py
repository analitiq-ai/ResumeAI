from pathlib import Path

# Directory Paths
APP_DIR_PATH = "resume_ai"
USER_DATA_DIR_PATH = Path("user_data/")
APP_DATA_DIR_PATH = Path("app/app_data/")
JOB_DESCRIPTION_DIR_PATH = USER_DATA_DIR_PATH / "jobs"
JOBS_FILE = "jobs.json"
JOB_DESCRIPTION_PROCESSED_DIR_PATH = USER_DATA_DIR_PATH / "jobs_processed"
JOBS_PROCESSED_FILE = "jobs_processed.json"
RESUMES_OLD_DIR_PATH = USER_DATA_DIR_PATH / "resumes"
RESUMES_NEW_YAML_DIR_PATH = APP_DATA_DIR_PATH / "resumes_yaml"
