import hashlib
from datetime import datetime
from typing import List, Dict
from copy import deepcopy

def generate_metadata(doc_data:dict, file_path, version="1", is_latest=True):
    content = doc_data["content"]
    page_list = doc_data["page_range"]
    
    if len(page_list) == 1:
        # Page값은 그냥 리스트안의 객체값(숫자)로 처리한다.
        page = page_list[0]
    else:
        # 일단 전체 리스트를 순환하면서 다 int값으로 변경하고
        # 만약 하나가 아니라면 숫자를 크기별로 정렬시킨다음에
        # 가장 작은 값을 앞에, 가장 큰 값을 뒤에두고
        # 중간에 "~"를 합쳐서 저장한다.
        
        page_list = [int(i) for i in page_list]
        page_list.sort()
        page = f"{page_list[0]}~{page_list[-1]}"
    
    file_name = file_path.split("/")[-1]
    doc_id = hashlib.md5(file_path.encode('utf-8')).hexdigest()
    content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
    
    metadata = {
        "doc_id": doc_id,
        "path": file_path,
        "file_name": file_name,
        "page" : page,
        
        "last_modified": datetime.now().isoformat(),
        "content_hash": content_hash,
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