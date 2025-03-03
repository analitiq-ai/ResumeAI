import logging
import os
import datetime

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
    move_file,
    run_shell_cmd,
    update_key_in_place
)
from resume_ai.app.constants import (
    JOB_DESCRIPTION_DIR_PATH,
    JOB_DESCRIPTION_PROCESSED_DIR_PATH,
    RESUMES_OLD_DIR_PATH
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
output_file = f"run_{timestamp}.md"

def write_output(msg: str):
    with open(output_file, "a") as f:
        f.write(msg + "\n")

def process_job(job_mgr: JobManager, job_title: str, job_description: str, cover_letter_creator: CoverLetterCreator, file_name=None):

    """Processes a job by matching it to user preferences, creating a resume, and optionally a cover letter."""
    if CONFIG_DATA.get("match_job_to_user_pref"):
        logger.info("Matching job to user preferences")
        score = job_mgr.match_job_to_req(job_title, job_description)
        write_output(f" - Job match score: {score}")

        if score < CONFIG_DATA.get("match_job_to_user_pref_limit", 0):
            msg = f""" - Job match score {score} is below threshold: {CONFIG_DATA.get("match_job_to_user_pref_limit", 0)}"""
            logger.info(msg)
            write_output(msg)
            return

    success = False

    try:
        success, new_resume = job_mgr.create_resume(job_title, job_description)
    except Exception as e:
        logger.exception("Error creating resume: %s", e)
        write_output(f" - Error creating resume. Please see logs.")

    if success:

        output_folder_name = job_mgr.get_output_folder_name(job_title)

        clickable_link = f"[Click here to open the directory](./{output_folder_name})"
        write_output(f" - CV Directory: {clickable_link}")

        if CONFIG_DATA.get("write_cover_letter", False):
            cover_letter_creator.create_cover_letter(job_title, job_description, new_resume, output_folder_name)

        # Move the processed file if applicable
        if file_name:
            move_file(
                JOB_DESCRIPTION_DIR_PATH / file_name,
                JOB_DESCRIPTION_PROCESSED_DIR_PATH / file_name
            )

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
            'Summary',
            ['This is the summary of the profile as it relates to the job.']
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

            process_job(job_mgr, job_title, job_description, cover_letter_creator, job_data['file_name'])

    elif CONFIG_DATA.get("mode") == 'links':
        links = load_json(JOB_DESCRIPTION_DIR_PATH / "job_links.json")

        from resume_ai.app.classes.url_crawler import URLCrawler
        crawler = URLCrawler(llm_client)
        crawled_descriptions = crawler.crawl_urls(links)

        for job in crawled_descriptions:
            job_title = job.metadata.get("title", "No Title Found")
            write_output(f"""## Title: {job_title}""")
            write_output(f""" - [{job.metadata.get("source")}]({job.metadata.get("source")})""")

            job_description = job.page_content

            process_job(job_mgr, job_title, job_description, cover_letter_creator)

    print(f"Output saved to {output_file}")

if __name__ == "__main__":
    main()
