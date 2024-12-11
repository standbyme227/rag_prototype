# /src/preprocessing/new_preprocessor.py
import os
import json
import logging
from src.config import PROCESSED_DATA_DIR
from src.query.query import generate_response
from src.preprocessing.new_metadata_manager import generate_metadata, manage_versions

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def create_summary_prompt(data):
    
    prompt = f"""
# Instruction
- First, summarize the entire document.
- Second, divide the document into smaller, semantically meaningful chunks.

# Target Data
{data}

# Response Structure (Example)
{{
    "summary": {{
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

    first_doc = documents[0]
    summary_metadata = generate_metadata(first_doc, chunk_type="summary")
    summary_target_data = []
    for doc in documents:
        template = {
            "page": doc.metadata.get("page"),
            "content": doc.content,
        }
        
        summary_target_data.append(template)
    
    # LLM을 이용해서 전체내용 요약과 의미를 유지하며 청킹을 진행한다.
    # 추출된 데이터 형식은 json으로 첫 키값은 summary로 요약을 저장하고
    # 나머지는 청킹된 순서대로 키값을 부여한 뒤
    # value는 또 다시 2개의 키값을 가지는데, page_range와 content로 구성한다.
    # page_range는 청킹된 문서가 어떤 페이지들에 원래 있었는지를 나타낸다.
    # 완료된 response값을 받아서, 메타데이터를 처리하고 저장한다.
    
    prompt = create_summary_prompt(summary_target_data)
    response = generate_response(prompt, work_type="chunking")
    
    # response가 json형식인지 확인한다.
    # json이 아니라면 오류를 발생시킨다.
    
    if is_json_response(response):
        try:
            json_data = json.loads(response)
        except Exception as e:
            print(f"Error parsing JSON: {e}")
    else:
        raise ValueError("Response is not in JSON format.")
    
    
    