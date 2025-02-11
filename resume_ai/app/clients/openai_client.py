import logging
from langchain_openai import ChatOpenAI
from resume_ai.app.clients.base_llm_client import BaseLlm

class OpenAIClient(BaseLlm):
    """Wrapper for Large language models."""

    def connect(self):

        client = ChatOpenAI(temperature=0, model="gpt-4o")
        logging.info(f"LLM is set to OpenAI")
        return client
