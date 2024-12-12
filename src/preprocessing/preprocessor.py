# /src/preprocessing/preprocessor.py
import os
import logging
from src.config import PROCESSED_DATA_DIR
from src.preprocessing.splitter import split_text
from src.preprocessing.metadata_manager import generate_metadata, manage_versions

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def preprocess_documents(documents, chunk_size=1000, chunk_overlap=200):
    """
    문서 전처리: 메타데이터 구성, 청킹, 버전 관리 및 파일 저장.

    Args:
        documents (list[Document]): 로드된 문서 리스트.
        chunk_size (int): 청킹 크기.
        chunk_overlap (int): 청킹 겹침.

    Returns:
        list[Document]: 전처리된 문서 리스트.
    """
    processed_docs = []
    existing_documents = []  # 기존 문서 리스트 (DB에서 로드된다고 가정)

    total_count = len(documents)
    logging.info(f"#2 Preprocessing documents, total: {total_count} cnt")
    count = 0

    # 문서들을 순환한다.
    for doc in documents:
        
        # 메타데이터에서 path가 없으면 source를 path로 사용
        if 'path' not in doc.metadata:
            doc.metadata['path'] = doc.metadata.get('source', 'unknown')

        logging.info(f"Processing document [{count}/{total_count}]: {doc.metadata['path']}")
        metadata = generate_metadata(doc.metadata['path'], doc.page_content)
        doc.metadata.update(metadata)

        # 문서 청킹
        logging.info(f"Splitting document [{count}/{total_count}]: {doc.metadata['path']}")
        if len(doc.page_content) > chunk_size:
            chunked_docs = split_text(doc, chunk_size, chunk_overlap)
            for i, chunked_doc in enumerate(chunked_docs):
                # 각 청크에도 별도 메타데이터 생성 (version, doc_id 동일)
                chunk_metadata = generate_metadata(
                    chunked_doc.metadata['path'], 
                    chunked_doc.page_content,
                    version=chunked_doc.metadata['version'], 
                    is_latest=chunked_doc.metadata['is_latest']
                )
                chunked_doc.metadata.update(chunk_metadata)
                processed_docs.append(chunked_doc)

                # 파일 저장
                save_processed_document(chunked_doc, PROCESSED_DATA_DIR, chunk_index=count)
                count += 1
        else:
            processed_docs.append(doc)
            # 파일 저장
            save_processed_document(doc, PROCESSED_DATA_DIR, chunk_index=count)
            count += 1

    logging.info(f"Preprocessing done: {count}/{total_count}")

    # 버전 관리
    final_documents = []
    logging.info(f"#3 Managing versions, total: {len(processed_docs)} cnt")
    v_count = 0
    for new_doc in processed_docs:
        v_count += 1
        updated_docs = manage_versions(existing_documents, new_doc)
        # manage_versions 호출 후 기존 문서 리스트 갱신
        existing_documents = updated_docs
        logging.info(f"Managing version [{v_count}/{len(processed_docs)}]: {new_doc.metadata['path']}")

    # 최종 전처리 문서 반환
    return existing_documents

def save_processed_document(doc, output_dir, chunk_index=None):
    """
    전처리된 문서를 파일로 저장합니다.

    Args:
        doc (Document): 저장할 문서 객체.
        output_dir (str): 저장할 디렉토리 경로.
        chunk_index (int, optional): 청킹된 문서의 인덱스.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    base_name = os.path.basename(doc.metadata['path'])
    base_name = os.path.splitext(base_name)[0]  # 확장자 제거
    if chunk_index is not None:
        file_name = f"{base_name}_chunk{chunk_index}.txt"
    else:
        file_name = f"{base_name}.txt"

    output_path = os.path.join(output_dir, file_name)

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(doc.page_content)
        logging.info(f"Saved processed document: {output_path}")
    except Exception as e:
        logging.error(f"Error saving processed document {output_path}: {e}", exc_info=True)