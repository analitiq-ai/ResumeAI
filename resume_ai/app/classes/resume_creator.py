import logging

# Third-party imports
from langchain_core.output_parsers import JsonOutputParser
from langchain.prompts import PromptTemplate

# Local imports
from resume_ai.app.clients.openai_client import OpenAIClient
from resume_ai.app.prompts import (
    RESUME_TO_JOB_PROMPT,
    MATCH_RESUMES_PROMPTS
)
from resume_ai.app.funcs import (
    save_yaml_to_file,
    run_shell_cmd,
    text_to_filename,
    get_custom_instructions,
    display_matching_scores
)
from resume_ai.app.constants import (
    RESUMES_NEW_YAML_DIR_PATH
)
from resume_ai.app.models import CVRoot, JobMatchScore



class ResumeCreator:
    """
    A class responsible for creating resumes based on job descriptions
    and matching them to existing resumes.
    """
    def __init__(
            self,
            llm_client: OpenAIClient,
            current_resume: dict,
            example_yaml: dict,
            config_data: dict,
            user_name: str
    ) -> None:
        """
        :param llm_client: Instance of the language model client (e.g., OpenAIClient).
        :param current_resume: Dict representing the user's current resume.
        :param example_yaml: YAML dict used as a template for new resumes.
        :param config_data: Configuration data loaded from JSON.
        :param user_name: The user's name for file naming.
        """
        self.llm_client = llm_client
        self.current_resume = current_resume
        self.example_yaml = example_yaml
        self.config_data = config_data
        self.user_name = user_name

    def match_resumes_to_job(
            self,
            job_title: str,
            job_description: str,
            new_resume: dict
    ) -> None:
        """
        Match current and new resumes to the specified job.

        :param job_title: Title of the job.
        :param job_description: The job description text.
        :param new_resume: Dict representing the newly created resume.
        :return: None
        """
        logging.info("Matching current resume and new resume for job: %s", job_title)
        parser = JsonOutputParser(pydantic_object=JobMatchScore)
        prompt = PromptTemplate(
            template=MATCH_RESUMES_PROMPTS,
            input_variables=["job"],
            partial_variables={
                "current_resume": self.current_resume,
                "new_resume": new_resume,
                "job_title": job_title,
                "format_instructions": parser.get_format_instructions()
            },
        )

        response = self.llm_client.invoke_llm(prompt, job_description, parser)
        display_matching_scores(response)

    def create_resume(
            self,
            job_title: str,
            job_description: str
    ) -> tuple[bool, dict]:
        """
        Create a resume tailored to the specified job.

        :param job_title: Title of the job.
        :param job_description: The job description text.
        :return: A tuple of (success_flag, new_resume_dict).
        """
        parser = JsonOutputParser(pydantic_object=CVRoot)
        prompt = PromptTemplate(
            template=RESUME_TO_JOB_PROMPT,
            input_variables=["job"],
            partial_variables={
                "resume": self.current_resume,
                "example": self.example_yaml.get('cv'),
                "custom_instructions": get_custom_instructions(self.config_data),
                "format_instructions": parser.get_format_instructions()
            },
        )

        logging.info(f""" {"="*20} Creating resume for job: %s {"="*20} """, job_title)
        job_file_name_without_extension = text_to_filename(job_title)

        response = self.llm_client.invoke_llm(prompt, job_description, parser)
        new_cv_dict = response["cv"]

        # Merge generated CV into the example YAML
        job_specific_yaml = self.example_yaml.copy()
        job_specific_yaml['cv'] = new_cv_dict

        # Save the YAML to file
        job_descr_resume_filename = (
                RESUMES_NEW_YAML_DIR_PATH
                / f"{self.user_name}__{job_file_name_without_extension}_CV.yaml"
        )
        save_yaml_to_file(job_specific_yaml, job_descr_resume_filename)

        # Match the newly created resume to the job
        self.match_resumes_to_job(job_title, job_description, new_cv_dict)

        # Attempt to render the new resume
        render_cmd = (
            f'rendercv render "{job_descr_resume_filename}" '
            f'--output-folder-name "rendercv_output/{job_file_name_without_extension}"'
        )
        logging.info("Running command: %s", render_cmd)

        try:
            run_shell_cmd(render_cmd)
            return True, new_cv_dict
        except Exception as e:
            logging.exception("Error rendering resume: %s", e)
            raise