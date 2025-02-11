import boto3
import logging
from langchain_aws import ChatBedrock
from resume_ai.clients.base_llm_client import BaseLlm

class BedrockClient(BaseLlm):
    """Wrapper for Large language models."""

    def connect(self):
        region = 'eu-central-1'

        client = boto3.client(
            "bedrock-runtime",
            region_name=region
        )
        logging.info(f"LLM is set to AWS Bedrock")
        return ChatBedrock(
            client=client,
            region_name=region,
            provider='anthropic',
            model_id='anthropic.claude-3-5-sonnet-20240620-v1:0',
            model_kwargs={
                "temperature": 0,
                "max_tokens": 16000,
            },
            streaming=False,
        )


