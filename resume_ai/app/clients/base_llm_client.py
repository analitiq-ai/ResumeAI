import logging
from abc import ABC, abstractmethod
from typing import Any
import base64
from mimetypes import guess_type
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BaseLlm(ABC):
    """
    Base class for utilizing an LLM model abstraction, allowing flexible integration of different
    language learning models (LLMs) for processing input data, images, and generating outputs or responses.
    """

    def __init__(self):
        self.llm = self.connect()

    @abstractmethod
    def connect(self):
        """Create and return a connection to the LLM backend."""

    @staticmethod
    def image_binary_to_data_url(image_binary, mime_type='image/png'):
        logger.debug("Converting image binary to data URL.")
        base64_encoded_data = base64.b64encode(image_binary).decode('utf-8')
        return f"data:{mime_type};base64,{base64_encoded_data}"

    def local_image_to_data_url(self, image_path):
        logger.info("Converting local image to data URL: %s", image_path)
        mime_type, _ = guess_type(image_path)
        if mime_type is None:
            mime_type = 'image/png'
            logger.debug("MIME type not detected, defaulting to 'image/png'.")

        try:
            with open(image_path, "rb") as image_file:
                image_binary = image_file.read()
            return self.image_binary_to_data_url(image_binary, mime_type)
        except Exception as e:
            logger.error("Error reading image file: %s", e)
            raise

    def invoke_img_from_binary(self, image_binary, mime_type='image/png'):
        logger.info("Encoding image from binary data.")
        encoded_image = self.image_binary_to_data_url(image_binary, mime_type)
        return self.invoke_img(encoded_image)

    def invoke_img_from_path(self, image_path):
        logger.info("Encoding image from path: %s", image_path)
        encoded_image = self.local_image_to_data_url(image_path)
        return self.invoke_img(encoded_image)

    def invoke_img(self, encoded_image, prompt, parser):
        logger.info("Invoking LLM with encoded image.")
        try:
            prompt_template = HumanMessagePromptTemplate.from_template(
                template=[
                    {"type": "text", "text": prompt},
                    {"type": "text", "text": "{format_instructions}"},
                    {"type": "image_url", "image_url": "{encoded_image}"},
                ]
            )

            prompt = ChatPromptTemplate.from_messages([prompt_template])

            image_chain = prompt | self.llm | parser

            format_instructions = parser.get_format_instructions()
            response = image_chain.invoke(input={"encoded_image": encoded_image, "format_instructions": format_instructions})
            logger.info("Image processing successful.")

            return response
        except Exception as e:
            logger.error("Error during image processing: %s", e)
            raise

    def invoke_llm(self, prompt: Any, params_dic: dict, parser: Any = None):
        # {"job_title": job_title, "job_description": job_descr}
        try:
            # Check if the parser is provided
            if parser:
                table_chain = prompt | self.llm | parser
            else:
                table_chain = prompt | self.llm

            response = table_chain.invoke(params_dic)
            logger.info("LLM invocation successful.")

            return response
        except Exception as e:
            logger.error("Error during LLM invocation: %s", e)
            raise

