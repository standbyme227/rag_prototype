# /src/query/retriever.py
import logging
import os
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from src.embedding.vectorstore_handler import get_vectorstore
from langchain.schema import Document
# SelfQueryRetriever 관련 부분은 구현되지 않았으므로 주석 처리
# from langchain.retrievers import SelfQueryRetriever
# from langchain.chat_models import ChatOpenAI
# from langchain.chains.query_constructor.base import AttributeInfo

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

PROCESSED_DATA_DIR = "/Users/mini/not_work/playground/rag_protoype/processed_data"

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

def retrieve_relevant_documents(query, top_k=6, is_ensemble=True, is_test_version=False):
    """
    질의에 대해, is_ensemble에 따라 ensemble retriever (dense+BM25) 또는
    SelfQueryRetriever(미구현) 를 사용해 top_k개의 문서 검색.
    
    매 호출 시 데이터 및 벡터스토어, 리트리버를 재초기화.
    
    Args:
        query (str): 사용자 질의
        top_k (int): 상위 검색 문서 개수
        is_ensemble (bool): True이면 ensemble retriever 사용 (dense+BM25), False이면 SelfQueryRetriever 사용.

    Returns:
        list[Document]: 상위 top_k 개의 관련 문서 리스트
    """
    # 매 호출 시 데이터 로드
    actual_corpus = load_corpus_from_directory(PROCESSED_DATA_DIR)
    vectorstore = get_vectorstore(is_test_version=is_test_version)

    # 실제 코퍼스가 없을 경우 빈 결과 반환
    if not actual_corpus:
        logging.info("No documents available in processed_data directory.")
        return []

    # Dense & BM25 리트리버 재생성
    dense_retriever = vectorstore.as_retriever(search_kwargs={"k": top_k})
    bm25_retriever = BM25Retriever.from_texts(actual_corpus)

    # Ensemble retriever 재생성
    ensemble_retriever = EnsembleRetriever(
        retrievers=[dense_retriever, bm25_retriever],
        weights=[0.8, 0.2],
        limit=top_k
    )

    if is_ensemble:
        results = ensemble_retriever.get_relevant_documents(query)
    else:
        # SelfQueryRetriever 미구현 상태
        raise NotImplementedError("SelfQueryRetriever is not implemented yet.")

    if not results:
        logging.info("No relevant documents found.")
        return []

    logging.info(f"Found {len(results)} relevant documents for query: '{query}' (is_ensemble={is_ensemble})")
    return results