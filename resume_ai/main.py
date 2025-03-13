import logging
import os
import datetime

from pathlib import Path

# Third-party imports
from langchain.globals import set_verbose

# Local imports
from resume_ai.app.classes.context import RunContext
from resume_ai.app.clients.openai_client import OpenAIClient
from resume_ai.app.classes.job_manager import JobManager
from resume_ai.app.classes.sqlite_logger import JobLogger
from resume_ai.app.funcs import (
    load_yaml,
    load_pdf,
    load_json,
    load_txt_files_from_directory,
    move_processed_job,
    run_shell_cmd,
    update_key_in_place,
    filter_unprocessed_jobs,
    get_clean_user_name
)
from resume_ai.app.constants import (
    JOBS_DIR_PATH,
    RESUMES_OLD_DIR_PATH,
    JOBS_FILE,
)


def main() -> None:
    """
    Main entry point for processing the user's resumes/jobs based on configuration.
    """
    config_data = load_json("config.json")

    context = RunContext(
        db_client=JobLogger(config_data),
        llm_client = OpenAIClient(),
        run_log_file = Path(f"""logs/run_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.md"""),
        config_data = config_data
    )

    base_cv_cmd = (
        f'rendercv new "{context.config_data.get("name")}" '
        f'--theme "{context.config_data.get("theme")}"'
    )
    run_shell_cmd(base_cv_cmd)

    # Prepare the username & load the template YAML
    user_name = get_clean_user_name(context.config_data.get("name"))
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
        logging.debug(
            "Replaced 'welcome_to_RenderCV!' with 'Summary' in %s", yaml_template_cv
        )

    # Load the old resume
    current_resume = load_pdf(RESUMES_OLD_DIR_PATH / context.config_data.get('resume_filename'))

    # Set up an LLM client

    logging.info("Running in '%s' mode.", context.config_data.get('mode'))

    # Create class instances
    job_mgr = JobManager(
        context=context,
        current_resume=current_resume,
        example_yaml=example_yaml
    )

    # Process job descriptions
    if context.config_data.get("mode") == 'files':
        job_descriptions = load_txt_files_from_directory(JOBS_DIR_PATH)

        if not job_descriptions:
            logging.error("No job descriptions found in the job_descriptions directory.")
            raise SystemExit(1)

        for job_data in job_descriptions:
            context.db_client.clear_job_data()
            job_title = os.path.splitext(job_data['file_name'])[0]
            job_description = job_data['content']
            context.write_output(f"""## Title: {job_title}""")

            success = job_mgr.process_job(job_title, job_title, job_description)

            # Move the processed file
            if success:
                move_processed_job(context.config_data.get("mode"), job_data['file_name'])

    elif context.config_data.get("mode") == 'links':
        links = load_json(JOBS_DIR_PATH / JOBS_FILE)
        unique_links = list(set(links))

        if not unique_links:
            logging.error("No URLs found in the jobs file.")
            raise SystemExit(1)

        jobs_processed = context.db_client.get_distinct_links()

        # Filter unprocessed jobs
        unprocessed_unique_links = filter_unprocessed_jobs(unique_links, jobs_processed)

        if not unprocessed_unique_links:
            logging.error("All urls on the list have been processed before.")
            raise SystemExit(1)

        # If useragent is not set, set it
        user_agent = os.environ.get('USER_AGENT', None)
        if not user_agent:
            os.environ['USER_AGENT'] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

        from resume_ai.app.classes.url_crawler import URLCrawler
        crawler = URLCrawler(context.llm_client)
        crawled_descriptions = crawler.crawl_urls(unprocessed_unique_links)

        for job in crawled_descriptions:
            context.db_client.clear_job_data()
            job_link = job.metadata.get("source")
            context.db_client.add_job_data('url', job_link)
            job_title = job.metadata.get("title", "No Title Found")
            context.write_output(f"""## Title: {job_title}""")
            context.write_output(f""" - [{job_link}]({job_link})""")

            # check if job is active
            url_check = job_mgr.check_url_job_active(job_link, job_title, job.page_content)
            if not url_check.get('is_active') == True :
                context.db_client.add_job_data('job_title', job_title)
                context.db_client.add_job_data('status', 'inactive job')
                context.db_client.insert_job()
                context.write_output("\nJob is Inactive")
                logging.info(f"Job is Inactive: {job_link}")
                continue
            else:
                job_title = url_check.get('job_title')
                job_description = url_check.get('job_description')

            success = job_mgr.process_job(job_link, job_title, job_description)

            # Move the processed job link
            if success:
                move_processed_job(context.config_data.get("mode"), job_link)

    logging.info(f"Output saved to {context.run_log_file}")

if __name__ == "__main__":
    main()
