# /src/preprocessing/new_preprocessor.py
import os
import logging
from src.config import PROCESSED_DATA_DIR
from src.preprocessing.splitter import split_text
from src.preprocessing.new_metadata_manager import generate_metadata, manage_versions

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def preprocess_documents(documents, chunk_size=1000, chunk_overlap=200):
    # 문서를 전처리한다.
    # LLM을 이용해서 요약하고 저장한다.
    # 각각의 레이어를 구성해서 단계별로 진행될 수 있도록 한다.
    # 하면서 메타데이터도 신경을 써야한다.
    processed_docs = []
    existing_documents = []  # 기존 문서 리스트 (DB에서 로드된다고 가정)

    # 첫번째로 전체 문서에 대한 처리다.
    # 전체 문서에 대한 메타데이터를 생성한다.
    
    total_count = len(documents)
    logging.info(f"#2 Preprocessing documents, total: {total_count} cnt")
    page_num = documents.metadata.get("page", None)
    
    if not page_num:
        raise ValueError("Page number is not provided.")
    
    # 어떤 메타데이터가 구성이 되어야할까?
    # file_name, chunk_type, path, doc_id, last_modified, version, is_latest
    
    documents_data = []
    
    first_doc = documents[0]
    summary_metadata = generate_metadata(first_doc, chunk_type="summary")
    
    for doc in documents:
        pass