import logging
from datetime import datetime

# Third-party imports
from langchain.prompts import PromptTemplate
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

# Local imports
from resume_ai.app.clients.openai_client import OpenAIClient
from resume_ai.app.prompts import COVER_LETTER_PROMPT
from resume_ai.app.funcs import text_to_filename


class CoverLetterCreator:
    """
    A class responsible for creating a cover letter for a given job using a resume.
    """
    def __init__(self, llm_client: OpenAIClient) -> None:
        """
        :param llm_client: Instance of the language model client (e.g., OpenAIClient).
        """
        self.llm_client = llm_client

    def create_cover_letter(
            self,
            job_title: str,
            job_description: str,
            resume: dict
    ) -> None:
        """
        Create and save a cover letter as a PDF.

        :param job_title: Title of the job.
        :param job_description: The job description text.
        :param resume: Dict representing the resume data to pull details from.
        :return: None
        """
        logging.info("Writing cover letter for job: %s", job_title)
        formatted_date = datetime.now().strftime("%B %d, %Y")  # e.g., "March 19, 2024"

        prompt_create_cover_letter = PromptTemplate(
            template=COVER_LETTER_PROMPT,
            input_variables=["job"],
            partial_variables={
                "job_title": job_title,
                "job_description": job_description,
                "current_date": formatted_date,
                "resume": resume
            },
        )

        response = self.llm_client.invoke_llm(prompt_create_cover_letter, job_description)
        #logging.info("Cover letter text:\n%s", response.content)

        job_file_name_without_extension = text_to_filename(job_title)
        output_filename = (
            f"rendercv_output/{job_file_name_without_extension}/"
            f"{job_file_name_without_extension}__Cover_Letter.pdf"
        )
        logging.info("Writing cover letter to %s", output_filename)

        self.save_text_as_pdf(response.content, output_filename)

    @staticmethod
    def save_text_as_pdf(text: str, output_filename: str) -> None:
        """
        Save the given text content as a PDF.

        :param text: The text content to save.
        :param output_filename: The path at which to save the PDF.
        :return: None
        """
        doc = SimpleDocTemplate(output_filename, pagesize=letter)
        styles = getSampleStyleSheet()
        style = styles["Normal"]
        style.fontSize = 10
        style.leading = 12

        elements = []
        for line in text.split("\n"):
            if line.strip():
                elements.append(Paragraph(line, style))
                elements.append(Spacer(1, 12))

        doc.build(elements)
