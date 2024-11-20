from langchain.vectorstores import Chroma
from langchain.schema import Document
from src.config import VECTORSTORE_DIR

def save_to_vectorstore(chunks, metadata):
    vectorstore = Chroma(persist_directory=VECTORSTORE_DIR, embedding_function=None)
    docs = [Document(page_content=chunk, metadata=metadata) for chunk in chunks]
    vectorstore.add_documents(docs)
    vectorstore.persist()

def search_vectorstore(query, top_k=5):
    vectorstore = Chroma(persist_directory=VECTORSTORE_DIR, embedding_function=None)
    return vectorstore.similarity_search(query, k=top_k)