# backend/services/groq_service.py
from groq import Groq
from config import Config
import logging
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GroqService:
    _instance = None
    _client: Groq = None
    _llm_fast: ChatGroq = None
    _llm_accurate: ChatGroq = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GroqService, cls).__new__(cls)
            cls._instance._init_client()
        return cls._instance

    def _init_client(self):
        if Config.GROQ_API_KEY:
            self._client = Groq(api_key=Config.GROQ_API_KEY)
            self._llm_fast = ChatGroq(temperature=0, groq_api_key=Config.GROQ_API_KEY, model_name=Config.LLM_MODEL_FAST)
            self._llm_accurate = ChatGroq(temperature=0, groq_api_key=Config.GROQ_API_KEY, model_name=Config.LLM_MODEL_ACCURATE)
            logger.info("Groq client and Langchain models initialized.")
        else:
            logger.error("GROQ_API_KEY is not set in config. Groq service will not be available.")

    def get_client(self) -> Groq:
        return self._client

    def get_llm_fast(self) -> ChatGroq:
        return self._llm_fast

    def get_llm_accurate(self) -> ChatGroq:
        return self._llm_accurate

    async def chat_completion(self, prompt: str, user_message: str, model: str = Config.LLM_MODEL_FAST) -> str:
        """
        Performs a chat completion using Groq's native API.
        More direct control over API call.
        """
        if not self._client:
            raise ValueError("Groq client not initialized.")
        try:
            chat_completion = await self._client.chat.completions.create(
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_message},
                ],
                model=model,
                temperature=0.0,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Error with Groq chat completion (model: {model}): {e}")
            raise

    async def invoke_llm_chain(self, system_prompt: str, user_message: str, model_type: str = "fast") -> str:
        """
        Invokes a Langchain LLM chain for more structured interactions.
        Uses predefined LLM models (fast or accurate).
        """
        llm = self.get_llm_fast() if model_type == "fast" else self.get_llm_accurate()
        if not llm:
            raise ValueError("LLM model not initialized.")

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{input}")
        ])
        output_parser = StrOutputParser()
        chain = prompt | llm | output_parser

        try:
            response = await chain.ainvoke({"input": user_message})
            return response
        except Exception as e:
            logger.error(f"Error invoking LLM chain (model_type: {model_type}): {e}")
            raise

# Global instance for easy access
groq_service = GroqService()