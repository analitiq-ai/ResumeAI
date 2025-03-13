from langchain_community.document_loaders import AsyncHtmlLoader
from langchain_community.document_transformers import Html2TextTransformer


class URLCrawler:
    """
    URLCrawler is responsible for asynchronously loading HTML content from a list of URLs
    and transforming it into plain text using a provided LangChain LLM object.

    Attributes:
        llm (object): An instance of a LangChain LLM-related object, used for transformations.
    """

    def __init__(self, llm) -> None:
        """
        Initialize the URLCrawler with the necessary LLM object.

        Args:
            llm: An object holding LLM client.
        """
        self.llm = llm

    def crawl_urls(self, urls: list[str]) -> list:
        """
        Asynchronously loads HTML content from a list of URLs and transforms it into plain text.

        Args:
            urls (list[str]): A list of URLs to crawl.

        Returns:
            list: A list of transformed documents, where each document's content is plain text.
        """
        # Load HTML documents from the URLs
        loader = AsyncHtmlLoader(urls)
        docs = loader.load()

        # Transform the documents to plain text
        html2text = Html2TextTransformer()
        docs_transformed = html2text.transform_documents(docs)

        return docs_transformed
