from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
VECTOR_DATABASE_URL = os.getenv("VECTOR_DATABASE_URL")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
CHAT_MODEL = os.getenv("CHAT_MODEL")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")

if not VECTOR_DATABASE_URL:
    raise ValueError("VECTOR_DATABASE_URL is not set")

if not EMBEDDING_MODEL:
    raise ValueError("EMBEDDING_MODEL is not set")

if not CHAT_MODEL:
    raise ValueError("CHAT_MODEL is not set")
    