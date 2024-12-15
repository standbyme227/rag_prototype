# /src/query/retriever.py
import logging
import os
from langchain.retrievers import EnsembleRetriever
from langchain.retrievers import EnsembleRetriever
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor
from src.embedding.vectorstore_handler import VectorStoreManager
from langchain.schema import Document
from src.config import VECTORSTORE_VERSION
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

PROCESSED_DATA_DIR = "/Users/mini/not_work/playground/rag_protoype/processed_data"

# 전역 변수로 리트리버를 저장
_retriever = None

vectorstore = VectorStoreManager.get_instance()

def load_corpus_from_directory(directory):
    corpus = []
    if not os.path.exists(directory):
        logging.warning(f"Directory does not exist: {directory}")
        return corpus

    for filename in os.listdir(directory):
        if filename.endswith(".txt"):
            file_path = os.path.join(directory, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read().strip()
                    if text:
                        corpus.append(text)
            except Exception as e:
                logging.error(f"Error reading {file_path}: {e}", exc_info=True)
    return corpus

def _create_retriever(vectorstore_version=VECTORSTORE_VERSION, top_k=6):
    """리트리버 생성 및 초기화"""
    dense_retriever = vectorstore.as_retriever(search_kwargs={"k": top_k})

    # if vectorstore.get()['metadatas'] and vectorstore.get()['metadatas'][0] and vectorstore.get()['metadatas'][0].get('source'):
    #     logging.info("Using metadata from vectorstore for BM25 retriever.")
    #     bm25_texts = [doc.get('source') for doc in vectorstore.get()['metadatas']]
    #     bm25_retriever = BM25Retriever.from_texts(bm25_texts)
    # else:
    #     logging.info("Using file system for BM25 retriever.")
    #     actual_corpus = load_corpus_from_directory(PROCESSED_DATA_DIR)
    #     bm25_retriever = BM25Retriever.from_texts(actual_corpus)
    
    # ensemble_retriever = EnsembleRetriever(
    #     retrievers=[dense_retriever, bm25_retriever],
    #     weights=[0.8, 0.2],
    #     # limit=6  # 이 부분 제거
    # )

    # # Gemini 모델 초기화
    # llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
    # compressor = LLMChainExtractor.from_llm(llm)
    # compression_retriever = ContextualCompressionRetriever(base_compressor=compressor, base_retriever=ensemble_retriever)

    return {
        "dense": dense_retriever,
        # "bm25": bm25_retriever,
        # "ensemble": ensemble_retriever,
        # "compression": compression_retriever
    }


def retrieve_relevant_documents(query, top_k=6, vectorstore_version=VECTORSTORE_VERSION, retriever_type="dense"):
    """
    질의에 대해, 지정된 리트리버를 사용하여 top_k개의 문서 검색.
    
    Args:
        query (str): 사용자 질의
        top_k (int): 상위 검색 문서 개수
        retriever_type (str): 사용할 리트리버 타입 ("dense", "bm25", "ensemble", "compression")

    Returns:
        list[Document]: 상위 top_k 개의 관련 문서 리스트
    """
    global _retriever
    if _retriever is None:
        _retriever = _create_retriever(vectorstore_version=vectorstore_version, top_k=top_k)

    if retriever_type not in _retriever:
        logging.error(f"Retriever type '{retriever_type}' not found.")
        return []
    
    retriever = _retriever[retriever_type]

    if retriever_type in ["dense", "bm25"]:
        retriever.search_kwargs["k"] = top_k
    elif retriever_type == "ensemble":
        # EnsembleRetriever는 limit을 직접 설정할 수 없으므로, 내부 리트리버의 k값을 수정
        for r in retriever.retrievers:
            if hasattr(r, 'search_kwargs'):
                r.search_kwargs['k'] = top_k
    elif retriever_type == "compression":
        retriever.base_retriever.limit = top_k

    results = retriever.get_relevant_documents(query)

    if not results:
        logging.info("No relevant documents found.")
        return []

    logging.info(f"Found {len(results)} relevant documents for query: '{query}' (retriever_type={retriever_type})")
    return results