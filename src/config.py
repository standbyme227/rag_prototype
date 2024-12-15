import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Paths
DATA_DIR = "./data"
PROCESSED_DATA_DIR = "./processed_data"

# Vectorstore
V0_VECTORSTORE_DIR = "./vectorstore/v0"
V1_VECTORSTORE_DIR = "./vectorstore/v1"
# VECTORSTORE_DIR = "./vectorstore"
TEST_VECTORSTORE_DIR = "./test_vectorstore"

VECTORSTORE_VERSION = "v1"

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") # for embedding
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") # for query

# Extra Variables
RETRIEVER_TYPE = os.getenv("RETRIEVER_TYPE", "ensemble")