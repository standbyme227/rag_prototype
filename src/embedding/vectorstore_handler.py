# src/embedding/vectorstore_handler.py
import os
import logging
from langchain_chroma import Chroma
from langchain.schema import Document
from src.embedding.embedder import (
        CustomOpenAIEmbeddings, 
        # CustomGoogleEmbeddings,
    )
from src.config import (
        VECTORSTORE_DIR, 
        TEST_VECTORSTORE_DIR
    )
from src.preprocessing.metadata_manager import generate_doc_id  # doc_id 생성 함수

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def get_vectorstore(directory=None, is_test_version=False):
    """
    Chroma 인스턴스를 생성하고 반환합니다. 
    VectorStore가 없는 경우 자동으로 초기화합니다.
    """
    
    # 설정된 디렉토리 확인
    if is_test_version:
        directory = TEST_VECTORSTORE_DIR
    else:
        directory = VECTORSTORE_DIR
    
    created = False
    # 디렉토리 존재 여부 확인 및 생성
    if not os.path.exists(directory):
        os.makedirs(directory)
        logging.info(f"Directory created at: {directory}")
        created = True
        
    
    # Chroma 초기화
    embedding_function = CustomOpenAIEmbeddings()
    vectorstore = Chroma(
        persist_directory=directory,
        embedding_function=embedding_function
    )
    
    # VectorStore 초기화 확인
    if len(vectorstore.get()["ids"]) == 0:
        if created:
            raise Exception("VectorStore initialization failed.")
        else:
            logging.info(f"VectorStore initialized at: {directory}")
    else:
        logging.info(f"VectorStore loaded with existing data at: {directory}")
    
    return vectorstore

def exists_in_vectorstore(doc_id, content_hash, is_test_version=False):
    """
    특정 doc_id와 content_hash를 가진 문서가 벡터스토어에 존재하는지 확인합니다.
    """
    
    if is_test_version is True:
        directory = TEST_VECTORSTORE_DIR
    else:
        directory = VECTORSTORE_DIR
        
    vectorstore = get_vectorstore(directory, is_test_version=is_test_version)
    
    try:
        results = vectorstore._collection.get(where={
            "$and": [
                {"doc_id": doc_id},
                {"content_hash": content_hash}
            ]
        })
        
        print(results)
        if results and results.get('documents'):
            # 해당 doc_id, content_hash 조합의 문서가 하나 이상 존재하면 True
            return True
        return False
    except Exception as e:
        logging.error(f"Error checking existence in vectorstore for doc_id={doc_id}, content_hash={content_hash}: {e}", exc_info=True)
        return False

def save_to_vectorstore(chunks, metadata_list, is_test_version=False):
    """
    텍스트 청크와 메타데이터를 받아 벡터스토어에 저장하기 전에
    doc_id와 content_hash 기반으로 중복 여부를 확인합니다.
    """
    
    if is_test_version is True:
        directory = TEST_VECTORSTORE_DIR
    else:
        directory = VECTORSTORE_DIR
    
    vectorstore = get_vectorstore(directory, is_test_version=is_test_version)
    docs_to_add = []
    
    for chunk, metadata in zip(chunks, metadata_list):
        doc_id = metadata.get("doc_id")
        content_hash = metadata.get("content_hash")
        
        if not doc_id or not content_hash:
            logging.warning("Metadata is missing 'doc_id' or 'content_hash'. Cannot reliably check duplicates.")
            # doc_id나 content_hash가 없다면 중복 확인 없이 추가
            docs_to_add.append(Document(page_content=chunk, metadata=metadata))
            continue

        # 중복 문서 확인
        if exists_in_vectorstore(doc_id, content_hash, is_test_version=is_test_version):
            logging.info(f"Document with doc_id={doc_id}, content_hash={content_hash} already exists. Skipping.")
            continue
        
        # 중복이 아니면 추가
        docs_to_add.append(Document(page_content=chunk, metadata=metadata))

    if docs_to_add:
        try:
            vectorstore.add_documents(docs_to_add)
            logging.info(f"Added {len(docs_to_add)} documents to vectorstore.")
        except Exception as e:
            logging.error(f"Error adding documents to vectorstore: {e}", exc_info=True)
    else:
        logging.info("No documents were added to vectorstore (all duplicates or empty input).")

def remove_from_vectorstore(file_path, remove_all_versions=True, is_test_version=False):
    """
    벡터스토어에서 특정 문서를 제거합니다.
    기존에는 file_path를 사용했으나, 이제는 doc_id를 사용합니다.
    file_path로부터 doc_id를 재생성한 뒤 해당 doc_id 관련 문서를 삭제.

    remove_all_versions=True 인 경우 해당 doc_id를 가진 모든 버전을 제거.
    필요하다면 version이나 content_hash를 추가로 사용해 특정 버전만 제거 가능.
    """
    doc_id = generate_doc_id(file_path)
    print("삭제하려는 문서의 doc_id:", doc_id)
    
    if is_test_version is True:
        directory = TEST_VECTORSTORE_DIR
    else:
        directory = VECTORSTORE_DIR
        
    vectorstore = get_vectorstore(directory, is_test_version=is_test_version)
    
    try:
        # doc_id 기반 문서 삭제
        # 모든 버전을 제거하려면 doc_id만 사용, 특정 버전 제거하려면 where에 'version': 특정값 추가
        # vectorstore.delete(where={"ids": doc_id})
        # vectorstore.delete(where={"doc_id": doc_id})
        vectorstore.delete(ids=[doc_id])
        logging.info(f"All documents with doc_id={doc_id} removed from vectorstore (origin: {file_path}).")
    except Exception as e:
        logging.error(f"Error removing documents from vectorstore for doc_id={doc_id}: {e}", exc_info=True)

def search_vectorstore(query, top_k=5, is_test_version=False):
    """
    벡터스토어에서 쿼리에 대한 유사한 문서를 검색합니다.
    """
    
    if is_test_version is True:
        directory = TEST_VECTORSTORE_DIR
    else:
        directory = VECTORSTORE_DIR
    
    vectorstore = get_vectorstore(directory=directory, is_test_version=is_test_version)
    try:
        results = vectorstore.similarity_search(query, k=top_k)
        return results
    except Exception as e:
        logging.error(f"Error searching vectorstore for query '{query}': {e}", exc_info=True)
        return []