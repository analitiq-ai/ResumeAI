from pathlib import Path

# Directory Paths
APP_DIR_PATH = "resume_ai"
USER_DATA_DIR_PATH = Path("user_data/")
APP_DATA_DIR_PATH = Path("app/app_data/")
JOBS_DIR_PATH = USER_DATA_DIR_PATH / "jobs"
JOBS_FILE = "jobs.json"
JOBS_PROCESSED_DIR_PATH = JOBS_DIR_PATH / "processed"
RESUMES_OLD_DIR_PATH = USER_DATA_DIR_PATH / "resumes"
RESUMES_NEW_YAML_DIR_PATH = APP_DATA_DIR_PATH / "resumes_yaml"
