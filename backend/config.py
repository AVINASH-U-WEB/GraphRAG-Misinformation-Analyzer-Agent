# backend/config.py
import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

class Config:
    NEO4J_URI = os.getenv('NEO4J_URI')
    NEO4J_USERNAME = os.getenv('NEO4J_USERNAME')
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    HUGGINGFACE_TOKEN = os.getenv('HUGGINGFACE_TOKEN')

    # LLM Model choices for Groq
    LLM_MODEL_FAST = "llama3-8b-8192"  # Faster, smaller context
    LLM_MODEL_ACCURATE = "llama3-70b-8192" # More capable, larger context

    # Other configurations
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() in ('true', '1', 't')
    SECRET_KEY = os.getenv('SECRET_KEY', 'super-secret-key-replace-me')