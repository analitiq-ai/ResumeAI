from dataclasses import dataclass
from pathlib import Path
from resume_ai.app.classes.sqlite_logger import JobLogger
from resume_ai.app.clients.openai_client import OpenAIClient

@dataclass
class RunContext:
    db_client: JobLogger
    llm_client: OpenAIClient
    run_log_file: Path
    config_data: dict


    def write_output(self, msg: str) -> None:
        with open(self.run_log_file, "a") as f:
            f.write(msg + "\n")