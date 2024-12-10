import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Paths
DATA_DIR = "./data"
PROCESSED_DATA_DIR = "./processed_data"
VECTORSTORE_DIR = "./vectorstore"

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]