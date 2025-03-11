import logging
import os
import datetime
import asyncio

# Third-party imports
from langchain.globals import set_verbose

# Local imports
from resume_ai.app.clients.openai_client import OpenAIClient
from resume_ai.app.classes.job_manager import JobManager
from resume_ai.app.classes.cover_letter_creator import CoverLetterCreator
from resume_ai.app.funcs import (
    load_yaml,
    load_pdf,
    load_json,
    load_txt_files_from_directory,
    display_job_to_user_req_matching_scores,
    move_processed_job,
    run_shell_cmd,
    update_key_in_place,
    filter_unprocessed_jobs,
    load_jobs_processed_urls,
    get_output_folder_name
)
from resume_ai.app.constants import (
    JOB_DESCRIPTION_DIR_PATH,
    RESUMES_OLD_DIR_PATH,
    JOBS_FILE,
)


# ----------------------------------------------------------------------------------
# Logging Setup
# ----------------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
stream_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

# ----------------------------------------------------------------------------------
# Global Settings
# ----------------------------------------------------------------------------------
set_verbose(False)

# ----------------------------------------------------------------------------------
# Load Config
# ----------------------------------------------------------------------------------
CONFIG_DATA = load_json("app/config.json")

# ----------------------------------------------------------------------------------
# Run output file
# ----------------------------------------------------------------------------------
# Generate timestamp
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

# Output file name with timestamp
run_log_file = f"logs/run_{timestamp}.md"

def write_output(msg: str):
    with open(run_log_file, "a") as f:
        f.write(msg + "\n")

async def run_async_jobs(job_mgr: JobManager, job_title: str, job_description: str, job_methods: list[str]):
    """
    Executes asynchronous jobs using specified methods from the job manager based on
    given job details.

    :param job_mgr: The job manager instance responsible for managing job execution.
    :type job_mgr: JobManager
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
        result = await asyncio.to_thread(getattr(job_mgr, method_name), job_title, job_description)
        return {method_name: result}

    results = await asyncio.gather(*(run_job(method) for method in job_methods))

    return {k: v for d in results for k, v in d.items()}

def process_job(job_mgr: JobManager, job_title: str, job_description: str, cover_letter_creator: CoverLetterCreator, job_identifier: str):
    """
    Processes a job description, including optional filtering of job preferences and automated resume and cover letter
    creation. The function uses the provided job manager and cover letter creator to perform these tasks. If configured,
    the job is evaluated for compatibility with user preferences before proceeding.

    :param job_mgr: Instance of `JobManager` responsible for handling job-related operations, such as matching user
        preferences and creating resumes.
    :type job_mgr: JobManager
    :param job_title: Title of the job being processed. Used for matching preferences and generating documents.
    :type job_title: str
    :param job_description: Detailed description of the job role. Used for both matching preferences and document
        generation.
    :type job_description: str
    :param cover_letter_creator: Instance of `CoverLetterCreator` used for generating customized cover letters for the job
        application if enabled in the configuration.
    :type cover_letter_creator: CoverLetterCreator
    :param job_identifier: Job title for text files and URL for links to the job postings
    :type job_identifier: str
    :return: Returns a boolean indicating whether the  process was successful.
    :rtype: bool

    """
    job_methods = ["get_job_req", "resume_improvements"]

    if CONFIG_DATA.get("match_job_to_user_pref"):
        logger.info("Matching job to user preferences")
        job_methods.append("match_job_to_req")

    # Run the async code
    results = asyncio.run(run_async_jobs(job_mgr, job_title, job_description, job_methods))

    # write key job requirements to the log
    write_output('\n**Job Key Requirements:** ' + results.get('get_job_req').get('job_requirements'))

    # write keywords to the log
    write_output('\n**Job Keywords:** ' + ', '.join(results.get('get_job_req').get('sentence_keywords')))

    #print(f"Resume improvements: {results['resume_improvements']}")

    if CONFIG_DATA.get("match_job_to_user_pref"):
        response = results['match_job_to_user_req']
        display_job_to_user_req_matching_scores(response)
        score = response['job_to_req_match_score']
        write_output(f" - Job match score: {score}")

        if score < CONFIG_DATA.get("match_job_to_user_pref_limit", 0):
            msg = f""" - Job match score {score} is below threshold: {CONFIG_DATA.get("match_job_to_user_pref_limit", 0)}"""
            logger.info(msg)
            write_output(msg)
            write_output(response['job_negatives'])
            return

    success = False

    output_folder_name = get_output_folder_name(job_identifier)

    try:
        success, new_resume = job_mgr.create_resume(job_title, job_description, output_folder_name, results.get('resume_improvements', None))
    except Exception as e:
        logger.exception("Error creating resume: %s", e)
        write_output(f" - Error creating resume. Please see logs.")

    if success:

        clickable_link = f"[Click here to open the directory](./{output_folder_name})"
        write_output(f" - CV Directory: {clickable_link}")

        if CONFIG_DATA.get("write_cover_letter", False):
            cover_letter_creator.create_cover_letter(job_title, job_description, new_resume, output_folder_name)

    return success

def main() -> None:
    """
    Main entry point for processing the user's resumes/jobs based on configuration.
    """
    # Create command to render a base CV via RenderCV
    base_cv_cmd = (
        f'rendercv new "{CONFIG_DATA.get("name")}" '
        f'--theme "{CONFIG_DATA.get("theme")}"'
    )
    run_shell_cmd(base_cv_cmd)

    # Prepare the username & load the template YAML
    user_name = CONFIG_DATA.get("name", "").replace(" ", "_")
    yaml_template_cv = f"{user_name}_CV.yaml"
    example_yaml = load_yaml(yaml_template_cv)

    # Fix up 'welcome_to_RenderCV!' section if it exists
    cv_sections = example_yaml.get('cv', {}).get('sections', {})
    if cv_sections.get('welcome_to_RenderCV!') is not None:
        example_yaml['cv']['sections'] = update_key_in_place(
            cv_sections,
            'welcome_to_RenderCV!',
            'summary',
            ['Hard working and experienced professional with a strong background in productive collaboration and teamwork.']
        )
        logger.debug(
            "Replaced 'welcome_to_RenderCV!' with 'Summary' in %s", yaml_template_cv
        )

    # Load the old resume
    current_resume = load_pdf(RESUMES_OLD_DIR_PATH / CONFIG_DATA.get("current_resume_name"))

    # Set up an LLM client
    llm_client = OpenAIClient()
    logger.info("Running in '%s' mode.", CONFIG_DATA.get("mode"))

    # Create class instances
    job_mgr = JobManager(
        llm_client=llm_client,
        current_resume=current_resume,
        example_yaml=example_yaml,
        config_data=CONFIG_DATA,
        user_name=user_name
    )
    cover_letter_creator = CoverLetterCreator(
        llm_client=llm_client,
        user_name=user_name
    )

    # Process job descriptions
    if CONFIG_DATA.get("mode") == 'files':
        job_descriptions = load_txt_files_from_directory(JOB_DESCRIPTION_DIR_PATH)

        if not job_descriptions:
            logger.error("No job descriptions found in the job_descriptions directory.")
            raise SystemExit(1)

        for job_data in job_descriptions:
            job_title = os.path.splitext(job_data['file_name'])[0]
            job_description = job_data['content']
            write_output(f"""## Title: {job_title}""")

            success = process_job(job_mgr, job_title, job_description, cover_letter_creator, job_title)

            # Move the processed file if applicable
            if success:
                move_processed_job(CONFIG_DATA.get("mode"), job_data['file_name'])

    elif CONFIG_DATA.get("mode") == 'links':
        links = load_json(JOB_DESCRIPTION_DIR_PATH / JOBS_FILE)
        unique_links = list(set(links))

        jobs_processed = load_jobs_processed_urls()

        # Filter unprocessed jobs
        unprocessed_unique_links = filter_unprocessed_jobs(unique_links, jobs_processed)

        if not unprocessed_unique_links:
            logger.error("No unprocessed jobs found.")
            raise SystemExit(1)

        # If useragent is not set, set it
        user_agent = os.environ.get('USER_AGENT', None)
        if not user_agent:
            os.environ['USER_AGENT'] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

        from resume_ai.app.classes.url_crawler import URLCrawler
        crawler = URLCrawler(llm_client)
        crawled_descriptions = crawler.crawl_urls(unprocessed_unique_links)

        for job in crawled_descriptions:
            job_link = job.metadata.get("source")
            job_title = job.metadata.get("title", "No Title Found")
            write_output(f"""## Title: {job_title}""")
            write_output(f""" - [{job_link}]({job_link})""")

            job_description = job.page_content

            success = process_job(job_mgr, job_title, job_description, cover_letter_creator, job_link)

            # Move the processed job link
            if success:
                move_processed_job(CONFIG_DATA.get("mode"), job_link)

    logger.info(f"Output saved to {run_log_file}")

if __name__ == "__main__":
    main()
