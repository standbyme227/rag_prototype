# /src/preprocessing/new_preprocessor.py
import os
import json
import logging
# from src.config import PROCESSED_DATA_DIR
from src.query.query import generate_response
from langchain.schema import Document
from src.preprocessing.new_metadata_manager import generate_metadata, manage_versions

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def create_summary_prompt(data):
    
    prompt = f"""
# Instruction
- First, divide the **entire document** into smaller, semantically meaningful chunks, without altering the original content.
- Second, summarize the **entire document**.

# Target Data
{data}

# Response Structure (Example : for 4 pages)
{{
    "summary": {{
        page_range: [1, 2, 3, 4],
        "content": "This is a summary of the entire document."
    }},
    "chunk_1": {{
        "page_range": [1, 2],
        "content": "This is the first chunk of the document."
    }},
    "chunk_2": {{
        "page_range": [3, 4],
        "content": "This is the second chunk of the document."
    }}
    ...
}}
"""

    return prompt

def set_document_data(documents_json_data, file_path):
    """
    문서 데이터를 Document 객체로 변환합니다.

    Args:
        documents_json_data (list[dict]): 문서 데이터 리스트.

    Returns:
        list[Document]: Document 객체 리스트.
    """
    documents = []
    for doc_data in documents_json_data.values():
        metadata = generate_metadata(doc_data, file_path)
        
        doc = Document(
            page_content=doc_data["content"],
            metadata=metadata
        )
        documents.append(doc)
    return documents

def is_json_response(response_content):
    """
    LLM 응답이 JSON 형식인지 확인합니다.

    Args:
        response_content (str): LLM 응답 문자열.

    Returns:
        bool: JSON 형식이면 True, 아니면 False.
    """
    try:
        json.loads(response_content)
        return True
    except json.JSONDecodeError:
        return False

def preprocess_documents(documents, chunk_size=1000, chunk_overlap=200):
    # 문서를 전처리한다.
    # LLM을 이용해서 요약하고 저장한다.
    # 각각의 레이어를 구성해서 단계별로 진행될 수 있도록 한다.
    # 하면서 메타데이터도 신경을 써야한다.

    # 첫번째로 전체 문서에 대한 처리다.
    # 전체 문서에 대한 메타데이터를 생성한다.
    
    total_count = len(documents)
    logging.info(f"#2 Preprocessing documents, total: {total_count} cnt")
    # page_num = documents[0].metadata.get("page", None)
    
    # if not page_num:
    #     raise ValueError("Page number is not provided.")
    
    # 어떤 메타데이터가 구성이 되어야할까?
    # file_name, chunk_type, path, doc_id, last_modified, version, is_latest

    first_doc = documents[0]
    file_path = first_doc.metadata.get("file_path")
    
    summary_target_data = []
    for doc in documents:
        template = {
            "page": doc.metadata.get("page"),
            "content": doc.page_content,
        }
        
        summary_target_data.append(template)
        
    # 띄어쓰기를 구분자로 사용해서 전체 내용을 구성한다.
    total_content = " ".join([doc.page_content for doc in documents])
    
    # LLM을 이용해서 전체내용 요약과 의미를 유지하며 청킹을 진행한다.
    # 추출된 데이터 형식은 json으로 첫 키값은 summary로 요약을 저장하고
    # 나머지는 청킹된 순서대로 키값을 부여한 뒤
    # value는 또 다시 2개의 키값을 가지는데, page_range와 content로 구성한다.
    # page_range는 청킹된 문서가 어떤 페이지들에 원래 있었는지를 나타낸다.
    # 완료된 response값을 받아서, 메타데이터를 처리하고 저장한다.
    
    prompt = create_summary_prompt(summary_target_data)
    
    retries_left = 3
    while True:
        # 현재 경로에 response.json이 있다면, 그 파일을 사용한다.
        if os.path.exists("response.json"):
            with open("response.json", "r") as f:
                response = f.read()
        else:
            response = generate_response(prompt, work_type="chunking")
            
            if response:
            # 현재 실행파일과 동일한 경로에 파일로 저장한다.
                save_path = os.path.join(os.getcwd(), "response.json")
                with open(save_path, "w") as f:
                    f.write(response)
        
        # response가 json형식인지 확인한다.
        # json이 아니라면 오류를 발생시킨다.
        # 앞쪽 "```json" 제거
        if response.startswith("```json"):
            response = response.strip("```json")
            
        # 뒤쪽 "```" 제거
        if "```" in response:
            response = response[:-4]
        
        if is_json_response(response):
            try:
                json_data = json.loads(response)
            except Exception as e:
                print(f"Error parsing JSON: {e}")
        else:
            raise ValueError("Response is not in JSON format.")
        
        # 아래의 형식을 참고해서 response도 처리한다.
        #total_content = "\n".join([f"{i+1}. {doc.page_content}" for i, doc in enumerate(documents)])
        total_response_content = ''
        for i in json_data:
            if i == "summary":
                pass
            else:
                total_response_content += json_data[i]["content"]
        
        diff = abs(len(total_content) - len(total_response_content))
        
        if diff < len(total_content) * 0.02:
            break
        else:
            retries_left -= 1
            if retries_left == 0:
                raise ValueError("Response content is too different from the original content.")
        
    cleaned_documents = set_document_data(documents_json_data=json_data, file_path=file_path)
    
    # # 기존에 vector로 저장되어있는 파일을 확인해서 각 문서 데이터의 버젼을 관리한다.
    # for doc in cleaned_documents:
    #     updated_docs = manage_versions(existing_documents, doc)
    #     existing_documents = updated_docs
    
    return cleaned_documents