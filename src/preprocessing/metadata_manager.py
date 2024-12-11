# /src/preprocessing/metadata_manager.py
import hashlib
from datetime import datetime

def generate_doc_id(file_path):
    """파일 경로 기반으로 문서를 식별하는 doc_id 생성."""
    return hashlib.md5(file_path.encode('utf-8')).hexdigest()

def generate_metadata(file_path, content, version=1, is_latest=True):
    """
    문서의 메타데이터를 생성합니다.

    Args:
        file_path (str): 문서 경로.
        content (str): 문서 내용.
        version (int): 문서 버전.
        is_latest (bool): 최신 문서 여부.

    Returns:
        dict: 메타데이터 딕셔너리.
    """
    doc_id = generate_doc_id(file_path)
    content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()

    # 어떤 메타데이터를 생성할지 정의
    metadata = {
        "doc_id": doc_id,
        "source": file_path,
        "path": file_path,
        "last_modified": datetime.now().isoformat(),
        "content_hash": content_hash,
        "version": version,
        "is_latest": is_latest,
        "type": file_path.split(".")[-1],  # 파일 확장자
    }
    # print(metadata)
    return metadata


def manage_versions(existing_documents, new_document):
    """
    문서 버전 관리 및 업데이트.
    doc_id를 기준으로 동일 문서 계열을 식별하고,
    content_hash를 통해 새로운 버전인지, 중복인지 판단합니다.

    Args:
        existing_documents (list[Document]): 기존 문서 리스트.
        new_document (Document): 새로운 문서.

    Returns:
        list[Document]: 업데이트된 문서 리스트.
    """
    updated_documents = []
    doc_id = new_document.metadata['doc_id']
    new_content_hash = new_document.metadata['content_hash']

    # 동일 doc_id를 가진 문서들 추출
    same_doc_id_docs = [doc for doc in existing_documents if doc.metadata.get('doc_id') == doc_id]
    
    if not same_doc_id_docs:
        # 첫 삽입 문서
        # version은 이미 1로 되어있으므로 그대로 삽입
        new_document.metadata['is_latest'] = True
        updated_documents = existing_documents + [new_document]
        return updated_documents

    # 기존 문서들 중 content_hash가 동일한 게 있는지 확인(중복 체크)
    for doc in same_doc_id_docs:
        if doc.metadata['content_hash'] == new_content_hash:
            # 동일한 문서(중복), 기존 문서를 그대로 유지
            # 기존 문서 중 latest인 것들은 그대로 latest 유지
            return existing_documents

    # 여기까지 왔다면 새로운 버전의 문서
    # 기존 same_doc_id_docs 중 latest 문서들의 version을 확인
    latest_versions = [doc for doc in same_doc_id_docs if doc.metadata.get('is_latest')]
    max_version = max(doc.metadata['version'] for doc in same_doc_id_docs) if same_doc_id_docs else 1

    # 이전 latest 문서들을 is_latest=False로 변경
    for doc in existing_documents:
        if doc.metadata.get('doc_id') == doc_id and doc.metadata.get('is_latest', False):
            doc.metadata['is_latest'] = False

    # 새로운 문서 버전 증가
    new_document.metadata['version'] = max_version + 1
    new_document.metadata['is_latest'] = True
    updated_documents = existing_documents + [new_document]

    return updated_documents