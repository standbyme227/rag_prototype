import hashlib
from datetime import datetime

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
    metadata = {
        "source": file_path,
        "path": file_path,
        "last_modified": datetime.now().isoformat(),
        "content_hash": hashlib.md5(content.encode()).hexdigest(),
        "version": version,
        "is_latest": is_latest,
        "type": file_path.split(".")[-1],  # 파일 확장자
    }
    return metadata


def manage_versions(documents, new_document):
    """
    문서 버전 관리 및 업데이트.

    Args:
        documents (list[Document]): 기존 문서 리스트.
        new_document (Document): 새로운 문서.

    Returns:
        list[Document]: 업데이트된 문서 리스트.
    """
    updated_documents = []
    is_duplicate = False

    for doc in documents:
        if doc.metadata['content_hash'] == new_document.metadata['content_hash']:
            is_duplicate = True
            updated_documents.append(doc)
        else:
            doc.metadata['is_latest'] = False  # 이전 문서를 최신 아님으로 설정
            updated_documents.append(doc)

    if not is_duplicate:
        updated_documents.append(new_document)  # 최신 문서를 추가

    return updated_documents