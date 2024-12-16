# /src/preprocessing/preprocessor_v1.py
import os
import json
import logging
# from src.config import PROCESSED_DATA_DIR
from src.query.query import generate_response
from langchain.schema import Document
from src.preprocessing.metadata_manager_v1 import generate_metadata, manage_versions

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def create_summary_prompt(data, total_content_text_count):
    
    minimum_chunk_count =  total_content_text_count // 500
    
    prompt = f"""
# Important Note

- The data is a text file in Korean.
- **The max size of each chunk should be between 500 characters.**
- The end value of the last range is equal to the length of total text.
- **The minimum number of chunks should be {minimum_chunk_count}.**
- If the last range of the chunks does not match the end of the total_content, you must request it again.


# Original Data (Text Length: {total_content_text_count})

- Data: {data}

# Response Template (Example: for 10 pages)

{{
    "summary": {{
        "content": "This is a summary of the entire document."
    }},
    "chunks":: [
        {{
            "id" : 1,
            "content_range": [0, 457]  # Start and end indices of the chunk in the concatenated content
            "reasoning": "This chunk covers the introduction section."
        }},
        {{
            "id" : 2,
            "content_range": [382, 567]  # Start and end indices of the chunk in the concatenated content, with overlap.
            "reasoning": "This chunk covers the first part of the main content."
        }},
        {{
            "id" : 3,
            "content_range": [513, 823]  # Start and end indices of the chunk in the concatenated content, with overlap.
            "reasoning": "This chunk covers the second part of the main content."
        }},
        ...
        {{
            "id" : n,
            "content_range": [x, y]  # Start and end indices of the chunk in the concatenated content, with overlap.
            "reasoning": "This chunk covers the last part of the main content."
        }},
    ]
}}

"""

    return prompt

def set_document_data(documents_json_data, file_path, origin_metadatas):
    """
    문서 데이터를 Document 객체로 변환합니다.

    Args:
        documents_json_data (list[dict]): 문서 데이터 리스트.

    Returns:
        list[Document]: Document 객체 리스트.
    """
    documents = []
    for key, value in documents_json_data.items():
        
        if key == "summary":
            doc_data = value
            metadata = generate_metadata(doc_data, file_path, origin_metadatas)
            
            doc = Document(
                    page_content=doc_data["content"],
                    metadata=metadata
                )
            documents.append(doc)
            
        elif key == "chunks":
            for doc_data in value:
                metadata = generate_metadata(doc_data, file_path, origin_metadatas)
        
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
    
def set_response_content(response, total_content):
    # 현재 response에 있는 데이터중 key값이 summary인 하나만 제외하고는 모두 content가 없다.
    # 왜냐면 chunking을 처리해서, 해당 페이지의 내용을 가져온게 아니라
    # 해당 청크의 범위를 가져온것이기 때문이다.
    # 그래서 total_content를 기반으로 response의 각 chunk의 content를 채워넣어야한다.
    
    total_overlap = 0
    prev_chunk = None
    
    chunks = response.get("chunks")
    
    # id로 정렬한다.
    chunks = sorted(chunks, key=lambda x: x["id"])
    chunk_count = len(chunks)
    
    for i in chunks:
        id = i["id"]
        content_range = i["content_range"]
        chunk_content = total_content[content_range[0]:content_range[1]]
        
        i["content"] = chunk_content
        
        if prev_chunk:
            prev_content_range = prev_chunk["content_range"]
            overlap = content_range[0] - prev_content_range[1] - 1
            total_overlap += overlap
            
        if i["id"] == chunk_count:
            last_value = content_range[1]
        prev_chunk = i
    
    response["chunks"] = chunks
    
    return response, total_overlap, last_value

def preprocess_documents(documents, chunk_size=1000, chunk_overlap=200):
    # 문서를 전처리한다.
    # LLM을 이용해서 요약하고 저장한다.
    # 각각의 레이어를 구성해서 단계별로 진행될 수 있도록 한다.
    # 하면서 메타데이터도 신경을 써야한다.

    # 첫번째로 전체 문서에 대한 처리다.
    # 전체 문서에 대한 메타데이터를 생성한다.
    
    total_count = len(documents)
    logging.info(f"#2 Preprocessing documents, total: {total_count} cnt")

    first_doc = documents[0]
    metadata = first_doc.metadata
    file_path = metadata.get("file_path")
    
    range_start = 0
    range_list = []
    for doc in documents:
        start = range_start
        end = range_start + len(doc.page_content)
        print(f"start: {start}, end: {end}")
        range_list.append([start, end])
        range_start = end + 1
        
        doc.metadata["content_range"] = [start, end]
    
    metadatas = [doc.metadata for doc in documents]
        
    # 전체 내용을 구성한다.
    total_content = "".join([doc.page_content for doc in documents])
    
    # LLM을 이용해서 전체내용 요약과 의미를 유지하며 청킹을 진행한다.
    # 추출된 데이터 형식은 json으로 첫 키값은 summary로 요약을 저장하고
    # 나머지는 청킹된 순서대로 키값을 부여한 뒤
    # value는 또 다시 2개의 키값을 가지는데, page_range와 content로 구성한다.
    # page_range는 청킹된 문서가 어떤 페이지들에 원래 있었는지를 나타낸다.
    # 완료된 response값을 받아서, 메타데이터를 처리하고 저장한다.
    
    total_content_text_count = len(total_content)
    prompt = create_summary_prompt(total_content, total_content_text_count)
    
    retries_left = 1
    while True:
        # # [테스트용]
        # # 현재 경로에 response.json이 있다면, 그 파일을 사용한다.
        # if os.path.exists("response.json"):
        #     with open("response.json", "r") as f:
        #         response = f.read()
        # else:
        #     response = generate_response(prompt, work_type="chunking")
            
        #     if response:
        #     # 현재 실행파일과 동일한 경로에 파일로 저장한다.
        #         save_path = os.path.join(os.getcwd(), "response.json")
        #         with open(save_path, "w") as f:
        #             f.write(response)
        
        response = generate_response(prompt, work_type="chunking")
        
        # response가 json형식인지 확인한다.
        # json이 아니라면 오류를 발생시킨다.
        # 앞쪽 "```json" 제거
        if response.startswith("```json"):
            response = response.strip("```json")
            
        # 뒤쪽 "```" 제거
        if "```" in response:
            response = response[:-4]
            # response = response.strip("```")
        
        if is_json_response(response):
            try:
                json_data = json.loads(response)
            except Exception as e:
                print(f"Error parsing JSON: {e}")
        else:
            # save_path = os.path.join(os.getcwd(), "response.json")
            # with open(save_path, "w") as f:
            #     f.write(response)
            raise ValueError("Response is not in JSON format.")
        
        json_data, total_overlap, last_value = set_response_content(json_data, total_content)      

        original_content_count = len(total_content)
        diff = abs(original_content_count - last_value)
        
        if diff < original_content_count * 0.02:
            break
        else:
            print(f"Diff입니다 : {diff}")
            retries_left -= 1
            if retries_left == 0:
                save_path = os.path.join(os.getcwd(), "response.json")
                with open(save_path, "w") as f:
                    f.write(response)
                raise ValueError("Response content is too different from the original content.")
    
    # json_data에 metadata를 추가한다.
    cleaned_documents = set_document_data(documents_json_data=json_data, file_path=file_path, origin_metadatas=metadatas)
    
    # # 기존에 vector로 저장되어있는 파일을 확인해서 각 문서 데이터의 버젼을 관리한다.
    # for doc in cleaned_documents:
    #     updated_docs = manage_versions(existing_documents, doc)
    #     existing_documents = updated_docs
    
    return cleaned_documents