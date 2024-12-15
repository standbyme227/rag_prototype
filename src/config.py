import os
from dotenv import load_dotenv

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 상위 디렉토리로 변경
DATA_DIR = os.path.join(BASE_DIR, "data")

# Load environment variables from .env
load_dotenv(os.path.join(BASE_DIR, '.env'), override=True)

PROCESSED_DATA_DIR = os.path.join(BASE_DIR, "processed_data")

# Vectorstore
V0_VECTORSTORE_DIR = os.path.join(BASE_DIR, "vectorstore/v0")
V1_VECTORSTORE_DIR = os.path.join(BASE_DIR, "vectorstore/v1")
# VECTORSTORE_DIR = "./vectorstore"
TEST_VECTORSTORE_DIR = "./test_vectorstore"

VECTORSTORE_VERSION = "v1"

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") # for embedding
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") # for query

# Extra Variables
RETRIEVER_TYPE = os.getenv("RETRIEVER_TYPE", "dense")