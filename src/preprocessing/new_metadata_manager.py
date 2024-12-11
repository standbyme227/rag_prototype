import hashlib
from datetime import datetime
from typing import List, Dict
from copy import deepcopy

def generate_metadata(doc, chunk_type="chunk", version="1", is_latest=True):

    content = doc.page_content
    metadata = doc.metadata
    
    file_path = metadata.get("path", "unknown")
    
    doc_id = hashlib.md5(file_path.encode('utf-8')).hexdigest()
    content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()

    if chunk_type == "chunk":
        page = metadata.get("page")
        if not page:
            raise ValueError("Page number is not provided.")
        
        metadata = {
            "doc_id": doc_id,
            "chunk_type": chunk_type,
            "path": file_path,
            "file_name": file_path.split("/")[-1],
            "page": page,
            "total_page": metadata.get("total_pages"),
            
            "content_hash": content_hash,
            
            "last_modified": datetime.now().isoformat(),
            "version": version,
            "is_latest": is_latest,
        }
    else:
        # chunk_type이 summary인 경우
        metadata = {
            "doc_id": doc_id,
            "chunk_type": chunk_type,
            "path": file_path,
            "file_name": file_path.split("/")[-1],
            "content_hash": content_hash,
            "last_modified": datetime.now().isoformat(),
            "version": version,
            "is_latest": is_latest,
        }
    
    return metadata

class Document:
    def __init__(self, metadata: Dict, content: str):
        self.metadata = metadata
        self.content = content

def manage_versions(existing_documents: List[Document], new_document: Document) -> List[Document]:
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

    # doc_id를 기준으로 문서를 그룹화한 딕셔너리 생성
    docs_by_id = {}
    for doc in existing_documents:
        if doc.metadata.get('doc_id') not in docs_by_id:
            docs_by_id[doc.metadata.get('doc_id')] = []
        docs_by_id[doc.metadata.get('doc_id')].append(doc)
    
    same_doc_id_docs = docs_by_id.get(doc_id, [])

    if not same_doc_id_docs:
        # 첫 삽입 문서
        new_document.metadata['version'] = 1
        new_document.metadata['is_latest'] = True
        updated_documents = existing_documents + [new_document]
        return updated_documents

    # 기존 문서들 중 content_hash가 동일한 게 있는지 확인(중복 체크)
    for doc in same_doc_id_docs:
        if doc.metadata['content_hash'] == new_content_hash:
            # 동일한 문서(중복), 기존 문서를 그대로 유지
            return existing_documents

    # 새로운 버전의 문서
    max_version = max((doc.metadata['version'] for doc in same_doc_id_docs), default=0)

    # 이전 latest 문서들을 is_latest=False로 변경
    updated_documents = []
    for doc in existing_documents:
        if doc.metadata.get('doc_id') == doc_id:
            updated_doc = deepcopy(doc)
            if updated_doc.metadata.get('is_latest', False):
                updated_doc.metadata['is_latest'] = False
            updated_documents.append(updated_doc)
        else:
            updated_documents.append(doc)

    # 새로운 문서 버전 증가
    new_document.metadata['version'] = max_version + 1
    new_document.metadata['is_latest'] = True
    updated_documents.append(new_document)

    return updated_documents