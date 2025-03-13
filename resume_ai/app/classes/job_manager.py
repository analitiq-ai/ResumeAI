import logging
import asyncio
from pathlib import Path
from dataclasses import dataclass

# Third-party imports
from langchain_core.output_parsers import JsonOutputParser
from langchain.prompts import PromptTemplate

# Local imports
from resume_ai.app.classes.cover_letter_creator import CoverLetterCreator
from resume_ai.app.classes.context import RunContext
from resume_ai.app.prompts import (
    RESUME_TO_JOB_PROMPT,
    MATCH_RESUMES_PROMPT,
    MATCH_USER_REQ_PROMPT,
    EXAMINE_JOB_REQUIREMENTS,
    LIST_RESUME_IMPROVEMENTS,
    CHECK_SCRAPED_PAGE
)
from resume_ai.app.funcs import (
    load_yaml,
    save_yaml_to_file,
    run_shell_cmd,
    get_job_dir,
    get_custom_instructions,
    display_resumes_to_job_matching_scores,
    clean_empty,
    get_output_folder_name,
    display_job_to_user_req_matching_scores,
    get_clean_user_name
)
from resume_ai.app.constants import (
    RESUMES_NEW_YAML_DIR_PATH,
    USER_DATA_DIR_PATH
)
from resume_ai.app.models import (
    CVRoot,
    ResumeJobMatchScore,
    UserJobMatchScore,
    JobRequirements,
    ResumeImprovements,
    JobDetails
)

@dataclass
class JobManager:
    """
    A class responsible for creating resumes based on job descriptions
    and matching them to existing resumes.
    """
    context: RunContext
    current_resume: dict
    example_yaml: dict

    def match_job_to_user_req(
            self,
            job_title: str,
            job_description: str
    ) -> float:
        """
        Matches a specific job to its corresponding requirements by utilizing
        underlying matching algorithms or logic. This method performs the core
        operation of linking or determining compatibility between job entities
        and given requirement criteria from the user.

        :return: Match result or status that indicates the relationship or compatibility
                 between the job and its requirements.
        :rtype: Any
        """
        logging.info("Matching user requirements job: %s", job_title)

        # Importing optional components (this is not best practice)
        user_data_path = Path(USER_DATA_DIR_PATH) / self.context.config_data.get('profile_filename')
        user_data = load_yaml(user_data_path)

        parser = JsonOutputParser(pydantic_object=UserJobMatchScore)
        prompt = PromptTemplate(
            template=MATCH_USER_REQ_PROMPT,
            input_variables=["job_title", "job_description"],
            partial_variables={
                "personal_info": user_data.get('personal_info'),
                "work_preferences": user_data.get('work_preferences'),
                "job_requirements": user_data.get('job_requirements'),
                "format_instructions": parser.get_format_instructions()
            },
        )

        response = self.context.llm_client.invoke_llm(prompt, {"job_title": job_title, "job_description": job_description}, parser)

        return response


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
        parser = JsonOutputParser(pydantic_object=ResumeJobMatchScore)
        prompt = PromptTemplate(
            template=MATCH_RESUMES_PROMPT,
            input_variables=["job_title", "job_description"],
            partial_variables={
                "current_resume": self.current_resume,
                "new_resume": new_resume,
                "job_title": job_title,
                "format_instructions": parser.get_format_instructions()
            },
        )

        response = self.context.llm_client.invoke_llm(prompt, {"job_title": job_title, "job_description": job_description}, parser)
        display_resumes_to_job_matching_scores(response)

        self.context.db_client.add_job_data('resume_match_score', response['old_resume_match_score'])
        self.context.db_client.add_job_data('resume_tailored_match_score', response['new_resume_match_score'])

    def create_resume(
            self,
            job_title: str,
            job_description: str,
            output_dir: str,
            resume_improvements: list[str] = None,
    ) -> tuple[bool, dict]:
        """
        Create a resume tailored to the specified job.

        :param job_title: Title of the job.
        :param job_description: The job description text.
        :param output_dir: directory where to put the resume.
        :param resume_improvements: a list of resume improvements recommended by the LLM.
        :return: A tuple of (success_flag, new_resume_dict).
        """
        custom_instructions_dict = self.context.config_data
        if resume_improvements:
            custom_instructions_dict['resume_improvements'] = resume_improvements

        parser = JsonOutputParser(pydantic_object=CVRoot)
        prompt = PromptTemplate(
            template=RESUME_TO_JOB_PROMPT,
            input_variables=["job_title", "job_description"],
            partial_variables={
                "resume": self.current_resume,
                "example": self.example_yaml.get('cv'),
                "custom_instructions": get_custom_instructions(custom_instructions_dict),
                "format_instructions": parser.get_format_instructions()
            },
        )

        logging.info(f""" {"="*20} Creating resume for job: %s {"="*20} """, job_title)
        job_file_name_without_extension = get_job_dir(job_title)

        response = self.context.llm_client.invoke_llm(prompt, {"job_title": job_title, "job_description": job_description}, parser)

        # LLM has a tendency to add empty items, like `extracurricular_activities: []`. We should remove them as rendercv throws an error.
        new_cv_dict = clean_empty(response["cv"])

        # Merge generated CV into the example YAML
        job_specific_yaml = self.example_yaml.copy()
        job_specific_yaml['cv'] = new_cv_dict

        user_name = get_clean_user_name(self.context.config_data.get("name"))

        # Save the YAML to file
        job_descr_resume_filename = (
                RESUMES_NEW_YAML_DIR_PATH
                / f"{user_name}__{job_file_name_without_extension}_CV.yaml"
        )
        save_yaml_to_file(job_specific_yaml, job_descr_resume_filename)

        # Match the newly created resume to the job
        self.match_resumes_to_job(job_title, job_description, new_cv_dict)


        # Attempt to render the new resume
        render_cmd = (
            f'rendercv render "{job_descr_resume_filename}" '
            f'--output-folder-name "{output_dir}"'
        )
        logging.info("Running command: %s", render_cmd)

        try:
            run_shell_cmd(render_cmd)
            return True, new_cv_dict
        except Exception as e:
            logging.exception("Error rendering resume: %s", e)
            raise

    def get_job_req(self, job_title: str, job_description: str) -> dict:

        parser = JsonOutputParser(pydantic_object=JobRequirements)
        prompt = PromptTemplate(
            template=EXAMINE_JOB_REQUIREMENTS,
            input_variables=["job_title", "job_description"],
            partial_variables={
                "format_instructions": parser.get_format_instructions()
            }
        )

        response = self.context.llm_client.invoke_llm(prompt, {"job_title": job_title, "job_description": job_description}, parser)

        return response

    def resume_improvements(self, job_title: str, job_description: str) -> dict:

        parser = JsonOutputParser(pydantic_object=ResumeImprovements)
        prompt = PromptTemplate(
            template=LIST_RESUME_IMPROVEMENTS,
            input_variables=["job_title", "job_description"],
            partial_variables={
                "user_resume": self.current_resume,
                "format_instructions": parser.get_format_instructions()
            }
        )

        response = self.context.llm_client.invoke_llm(prompt, {"job_title": job_title, "job_description": job_description}, parser)

        return response

    def check_url_job_active(self, job_link: str, page_title: str, page_content: str):
        parser = JsonOutputParser(pydantic_object=JobDetails)
        prompt = PromptTemplate(
            template=CHECK_SCRAPED_PAGE,
            input_variables=["page_title", "page_content"],
            partial_variables={
                "url": job_link,
                "format_instructions": parser.get_format_instructions()
            }
        )

        response = self.context.llm_client.invoke_llm(prompt, {"page_title": page_title, "page_content": page_content}, parser)

        return response

    def process_job(self, job_identifier: str, job_title: str, job_description: str):
        """
        Processes a job description, including optional filtering of job preferences and automated resume and cover letter
        creation. The function uses the provided job manager and cover letter creator to perform these tasks. If configured,
        the job is evaluated for compatibility with user preferences before proceeding.

        :param job_title: Title of the job being processed. Used for matching preferences and generating documents.
        :type job_title: str
        :param job_description: Detailed description of the job role. Used for both matching preferences and document
            generation.
        :type job_description: str
        :param job_identifier: Job title for text files and URL for links to the job postings
        :type job_identifier: str
        :return: Returns a boolean indicating whether the  process was successful.
        :rtype: bool

        """
        self.context.db_client.add_job_data('job_title',job_title)
        self.context.db_client.add_job_data('job_description',job_description)

        success = False
        job_methods = ["get_job_req", "resume_improvements"]

        if self.context.config_data.get("match_job_to_user_pref"):
            logging.info("Matching job to user preferences")
            job_methods.append("match_job_to_user_req")

        # Run the async code
        results = asyncio.run(self.run_async_jobs(job_title, job_description, job_methods))

        # write key job requirements to the log
        self.context.write_output('\n**Job Key Requirements:** ' + results.get('get_job_req').get('job_requirements'))

        # write keywords to the log
        job_keywords = ', '.join(results.get('get_job_req').get('sentence_keywords'))
        self.context.write_output('\n**Job Keywords:** ' + job_keywords)
        self.context.db_client.add_job_data('job_keywords', job_keywords)

        #print(f"Resume improvements: {results['resume_improvements']}")

        if self.context.config_data.get("match_job_to_user_pref"):
            response = results['match_job_to_user_req']
            display_job_to_user_req_matching_scores(response)
            score = response['job_to_req_match_score']
            self.context.write_output(f" - Job match score: {score}")

            self.context.db_client.add_job_data('job_match_score', response['job_to_req_match_score'])
            self.context.db_client.append_llm_text('job_positives', response['job_positives'])
            self.context.db_client.append_llm_text('job_negatives', response['job_negatives'])

            if score < self.context.config_data.get("match_job_to_user_pref_limit", 0):
                msg = f""" - Job match score {score} is below threshold: {self.context.config_data.get("match_job_to_user_pref_limit", 0)}"""
                logging.info(msg)
                self.context.write_output(msg)
                self.context.write_output(response['job_negatives'])
                self.context.db_client.add_job_data('status', 'job does not match profile')
                self.context.db_client.insert_job()

                return True # we return True for success because processing was error-free

        output_folder_name = get_output_folder_name(job_identifier)
        self.context.db_client.add_job_data('resume_tailored_dir', output_folder_name)

        try:
            success, new_resume = self.create_resume(job_title, job_description, output_folder_name, results.get('resume_improvements', None))
            self.context.db_client.add_job_data('resume_tailored_text', new_resume)
        except Exception as e:
            logging.exception("Error creating resume: %s", e)
            self.context.write_output(f" - Error creating resume. Please see logs.")

        if results.get('resume_improvements', None):
            self.context.db_client.append_llm_text('resume_improvements', results.get('resume_improvements'))

        if success:
            clickable_link = f"[Click here to open the directory](../{output_folder_name})"

            self.context.write_output(f" - CV Directory: {clickable_link}")
            self.context.db_client.add_job_data('status', 'resume created')

            if self.context.config_data.get("write_cover_letter", False):

                cover_letter_creator = CoverLetterCreator(
                    llm_client = self.context.llm_client,
                    user_name = get_clean_user_name(self.context.config_data.get("name"))
                )

                cover_letter_creator.create_cover_letter(job_title, job_description, new_resume, output_folder_name)

        self.context.db_client.insert_job()
        return success

    async def run_async_jobs(self, job_title: str, job_description: str, job_methods: list[str]):
        """
        Executes asynchronous jobs using specified methods from the job manager based on
        given job details.

        :param job_title: The title of the job.
        :type job_title: str
        :param job_description: The description of the job.
        :type job_description: str
        :param job_methods: A list of method names that define the actions
            to be performed for the job.
        :type job_methods: list[str]
        :return: A dictionary with method names as keys and their respective
            execution results as values.
        :rtype: dict[str, Any]
        """
        async def run_job(method_name: str):
            result = await asyncio.to_thread(getattr(self, method_name), job_title, job_description)
            return {method_name: result}

        results = await asyncio.gather(*(run_job(method) for method in job_methods))

        return {k: v for d in results for k, v in d.items()}