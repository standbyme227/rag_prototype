# /src/preprocessing/metadata_manager_v1.py
import hashlib
from datetime import datetime
from typing import List, Dict
from copy import deepcopy

def generate_doc_id(file_path):
    """파일 경로 기반으로 문서를 식별하는 doc_id 생성."""
    return hashlib.md5(file_path.encode('utf-8')).hexdigest()

def generate_metadata(doc_data:dict, file_path, origin_metadatas, version="1", is_latest=True):
    # chunking을 새롭게 처리했기 때문에.
    # 해당 chunking에 맞게 페이지값을 처리해야한다.
    # origin_metadatas에는 기존의 문서 하나의 페이지에 대한 content_range값이 들어있다.
    # 그러니 doc_data의 content_range값을 이용해서, 기존의 페이지 값을 가져온다.
    # 방법은 doc_data의 content_range값의 start와 end를 가져와서
    # origin_metadatas를 순환하며, 해당 페이지의 content_range값을 확인할 수 있으니까.
    # 그 시작값이 start보다 작거나 같다면, 일단 해당 페이지는 해당 doc의 첫 페이지이며.
    # 또다시 순환하면서, 특정 페이지의 끝값이 end보다 크거나 같다면, 해당 페이지는 해당 doc의 마지막 페이지이다.
    # 그걸 이용해서 시작 페이지 넘버와 끝 페이지 넘버를 가져온뒤
    # 리스트에 넣을때는 그 시작넘버와 끝넘버의 사이 정수들까지 찾아서 모두 넣는다.
    
    content = doc_data["content"]
    
    # content_range가 있는지 확인한다.
    if "content_range" not in doc_data:
        # metadata의 모든 페이지값을 넣는다.
        page_list = [i["page"] + 1 for i in origin_metadatas]
        content_role = "summary"
    else:
        doc_content_range = doc_data["content_range"]
        doc_start = doc_content_range[0]
        doc_end = doc_content_range[1]
        
        start_page = end_page = page_list = selected_start = selected_end = None
        
        # origin_metadata를 page순으로 정렬한다.
        origin_metadatas = sorted(origin_metadatas, key=lambda x: x["page"])
        
        start_list = [i["content_range"][0] for i in origin_metadatas]
        end_list = [i["content_range"][1] for i in origin_metadatas]
        
        # start_list와 end_list를 정렬한다.
        start_list.sort()
        end_list.sort()
        
        # start_list에서 doc_start보다 작거나 같은 값들 중 가장 큰 값을 가져온다.
        for i in start_list:
            if i <= doc_start:
                selected_start = i
            else:
                break
        
        # end_list에서 doc_end보다 크거나 같은 값들 중 가장 작은 값을 가져온다.
        for i in end_list:
            if i >= doc_end:
                selected_end = i
                break
        
        # origin_metadatas를 돌면서 content_range값을 확인한 뒤
        # selected_start와 같은 값을 ["content_range"][0]에 가지고 있는 페이지를 시작페이지로,
        # selected_end와 같은 값을 ["content_range"][1]에 가지고 있는 페이지를 끝페이지로 설정한다.
        
        # content_range의 start와 end값을 가져온다.
        for i in origin_metadatas:
            start = i["content_range"][0]
            end = i["content_range"][1]
            
            if start == selected_start:
                start_page = i["page"] + 1
                
            if end == selected_end:
                end_page = i["page"] + 1
                
            if start_page and end_page:
                break
            
        page_list = list(range(start_page, end_page + 1))
        content_role = "chunking"
        
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
        "content_role": content_role,
        "path": file_path,
        "file_name": file_name,
        "source_pages" : page,
        
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