import sys
import os

# 프로젝트 루트를 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# from src.config import VECTORSTORE_DIR
# from chromadb.config import Settings
# from chromadb import Client
from langchain_community.vectorstores import Chroma
# from langchain_community.embeddings import OpenAIEmbeddings
from src.embedding.embedder import CustomEmbeddings

# # PersistentClient 설정
path = '/Users/mini/not_work/playground/rag_protoype/vectorstore'
# client = Client(Settings(persist_directory=path))

# # 컬렉션 목록 확인
# collections = client.list_collections()
# print(collections)

embedding_function = CustomEmbeddings()

# Chroma 데이터베이스 초기화
vectorstore = Chroma(
    persist_directory=path,
    embedding_function=embedding_function
)

docs = vectorstore.similarity_search("", k=5)
for doc in docs:
    print(doc.metadata)

