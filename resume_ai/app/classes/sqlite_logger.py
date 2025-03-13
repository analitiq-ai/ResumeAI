import sqlite3
import uuid
import json
from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel, Field

DB_FILE = "jobs.db"

# ---- Pydantic Models ---- #

class JobBatchConfig(BaseModel):
    """Stores batch-wide configurations that remain constant across jobs."""
    batch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mode: str  # "links" or "files"
    profile_filename: str
    resume_filename: str


class JobLogEntry(JobBatchConfig):
    """Extends batch config with job-specific fields."""
    created_ts: str = Field(default_factory=lambda: datetime.now().isoformat())
    url: Optional[str] = None
    job_title: str
    job_description: Optional[str] = None
    job_keywords: Optional[str] = None
    job_match_score: Optional[float] = None
    resume_match_score: Optional[float] = None
    resume_tailored_match_score: Optional[float] = None
    resume_tailored_dir: Optional[str] = None
    resume_tailored_text: Optional[str] = None
    llm_text: Optional[str] = None
    status: str = 'Error'


# ---- Job Logger Class ---- #

class JobLogger:
    def __init__(self, config: Dict, db_path: str = DB_FILE):
        """
        Initialize JobLogger with batch-wide configuration.

        :param config: Dictionary containing mode, profile_filename, and resume_filename.
        """
        self.db_path = db_path
        self.connection = self._get_connection()
        self._create_table()
        self.batch_config = JobBatchConfig(**config)  # Store batch-wide settings
        self.job_data = {}

    def _get_connection(self):
        """Ensures a single-threaded SQLite connection is reused."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        return conn

    def _create_table(self):
        """Creates the job log table if it does not exist."""
        query = """
        CREATE TABLE IF NOT EXISTS job_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT NOT NULL CHECK(status IN ('job does not match profile', 'inactive job', 'resume created', 'Error')),
            batch_id TEXT NOT NULL,
            created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            url TEXT,
            mode TEXT NOT NULL CHECK(mode IN ('links', 'files')),
            job_title TEXT NOT NULL,
            job_description TEXT,
            job_keywords TEXT,
            job_match_score REAL,
            profile_filename TEXT,
            resume_filename TEXT,
            resume_match_score REAL,
            resume_tailored_match_score REAL,
            resume_tailored_text TEXT,
            resume_tailored_dir TEXT,
            llm_text JSONB
        );
        """
        cursor = self.connection.cursor()
        cursor.execute(query)
        self.connection.commit()

    def insert_job(self):
        """
        Inserts a new job log entry, merging batch-wide and job-specific data.
        """
        job_data = self.job_data
        try:
            full_job_data = {**self.batch_config.model_dump(), **job_data}  # Merge batch settings

            # Ensure dictionary columns are stored as a JSON string
            cols = ["llm_text", "resume_tailored_text"]
            for col in cols:
                if col in full_job_data and isinstance(full_job_data[col], dict):
                    full_job_data[col] = json.dumps(full_job_data[col])

            job_entry = JobLogEntry(**full_job_data)  # Validate with Pydantic

            columns = ', '.join(job_entry.model_dump().keys())
            placeholders = ', '.join(['?' for _ in job_entry.model_dump()])
            values = tuple(job_entry.model_dump().values())

            query = f"INSERT INTO job_log ({columns}) VALUES ({placeholders})"
            cursor = self.connection.cursor()
            cursor.execute(query, values)
            self.connection.commit()
        except Exception as e:
            print(f"Error inserting job log: {e}")

    def get_distinct_links(self) -> list:
        """
        Extracts and returns a list of distinct URLs from the job_log table where the mode is 'links'
        and the URL is not NULL. This operation is performed by executing an SQL query, processed through
        an active database connection.

        :return: A list of distinct URLs where `mode = 'links'` and `url IS NOT NULL`.
        :rtype: list
        """
        query = "SELECT DISTINCT url FROM job_log WHERE mode = 'links' AND url IS NOT NULL"
        cursor = self.connection.cursor()
        cursor.execute(query)
        return [row[0] for row in cursor.fetchall() if row[0]]

    def close_connection(self):
        """Closes the database connection."""
        self.connection.close()

    def add_job_data(self, key: str, value):
        """
        Adds a new key-value pair to the job data dictionary.

        This method updates the `job_data` dictionary by adding a new key-value pair.
        If the key already exists in the dictionary, its value will be overwritten
        with the new value provided.

        :param key: The key to represent the data being stored.
        :type key: str
        :param value: The value to associate with the given key. The type of value is
            flexible and can be of any valid Python data type.
        """
        self.job_data[key] = value

    def append_llm_text(self, key: str, value: str) -> None:
        """
        Appends a key-value pair to the 'llm_text' dictionary within the
        `job_data` attribute. If the `llm_text` dictionary does not exist,
        it initializes it before appending.

        :param key: The key for the value to be added to the `llm_text` dictionary.
        :type key: str
        :param value: The value to be associated with the key in the `llm_text` dictionary.
        :type value: str
        """
        if not self.job_data.get('llm_text'):
            self.job_data['llm_text'] = {}

        self.job_data['llm_text'][key] = value

    def clear_job_data(self):
        """
        Clears the job data stored in the object. This function resets the `job_data`
        attribute to an empty dictionary. It is useful for resetting or cleaning up
        state that holds job-related information.

        :return: None
        """
        self.job_data = {}