# /src/query/llm_intergration.py
import os
import json
from src.config import DATA_DIR
from langchain_community.chat_models import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage  # Import HumanMessage
from src.query.retriever import retrieve_relevant_documents
from src.config import RETRIEVER_TYPE

FILE_LIST_PATH = os.path.join(DATA_DIR, "file_list.json")

def get_stored_file_list():
    from main import create_file_list, save_file_list
    
    if os.path.exists(FILE_LIST_PATH):
        with open(FILE_LIST_PATH, 'r', encoding='utf-8') as f:
            file_list = json.load(f)
            
            if not isinstance(file_list, list):
                raise ValueError("file_list.json should contain a list of file entries.")
    else:
        file_list = create_file_list()
        save_file_list(file_list)
    
    return file_list
        

def fetch_top_documents(query, top_k=5, is_test_version=False):
    """
    주어진 질문에 대해 상위 N개의 관련 문서를 검색합니다.

    Args:
        query (str): 사용자의 질문.
        top_k (int): 상위 N개의 문서를 가져옵니다.

    Returns:
        list: 상위 문서 리스트.
    """
    documents = retrieve_relevant_documents(query, top_k=top_k, retriever_type=RETRIEVER_TYPE, is_test_version=is_test_version)
    if not documents:
        print("No relevant documents found.")
        return []
    return documents[:top_k]

def create_prompt(query, document_data):
    """
    질문과 문맥을 기반으로 LLM 프롬프트를 생성합니다.

    Args:
        query (str): 사용자의 질문.
        context (str): 문맥 정보.

    Returns:
        str: 생성된 프롬프트.
    """
    stored_file_list = get_stored_file_list()
    if not document_data:
        return (
            f"I couldn't find any relevant context to answer the question:\n\n"
            f"Question: {query}\n\n"
            f"Please provide a generic response or guidance based on common knowledge."
        )
    return (
        f"""### Stored File List
{stored_file_list}
        
### Question
{query}\n\n
        """
        f"{document_data}\n\n"
        f"Please structure your response clearly with appropriate line breaks for better readability."
    )
    

def set_document_data(top_documents):
    # document_data
    # print(top_documents)    
    documents = ""
    
    for i, d in enumerate(top_documents):
        m = d.metadata
        if not m:
            path = ""
        
        else:
            path = m["path"]
        
            if not path:
                path = m["source"]
        
        if path:    
            file_name = path.split("/")[-1]
        else:
            file_name = "Unknown"
        
        template = f"""
### Doc.{i}
- File Name: {file_name}
- Path: {path}
- Content: {d.page_content}
        """
        documents += (template + "\n")
    return documents

def generate_response(query, top_k=5, system_instruction=None, is_test_version=False, max_tokens=None):
    """
    질의에 대한 응답을 생성합니다.

    Args:
        query (str): 사용자의 질문.
        top_k (int): 상위 N개의 문서를 사용.
        system_instruction (str, optional): 모델의 동작 지침.

    Returns:
        str: LLM의 응답.
    """
    # # LLM 초기화 (ChatOpenAI 사용)
    # llm = ChatOpenAI(
    #     temperature=0.8, 
    #     model="gpt-4o-2024-08-06",  # Chat 모델 이름
    # )
    
    llm = ChatGoogleGenerativeAI(
        # model="gemini-1.5-flash",
        model="gemini-2.0-flash-exp",
        temperature=0.5,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )

    # 문서 검색
    top_documents = fetch_top_documents(query, top_k, is_test_version)
    
    # # context를 구성할때 하나씩 ID를 구성해서 처리
    # # doc.id가 아니라 숫자를 하나씩 증가시키는 방법으로 처리
    # context = "\n".join([f"{i+1}. {doc.page_content}" for i, doc in enumerate(top_documents)])
    # metadata = "\n".join([f"{i+1}. {doc.metadata}" for i, doc in enumerate(top_documents)])
    
    document_data = set_document_data(top_documents)
    # print(document_data)
    
    # 프롬프트 생성
    prompt = create_prompt(query, document_data)
    
    if not system_instruction:
        # system_instruction = "Please respond to the following question based on the provided Documents Data in Korean."
        system_instruction = """
You are a professional assistant responding to questions in Korean. 
Use only the information from the provided Documents Data to answer the following question.
Do not include any references to the source, such as page numbers or document details.
Provide clear, concise, and natural responses as if you are explaining directly to the user.
If the information cannot be derived from the provided data, politely inform the user that it is not available.
"""

    # 메시지 포맷에 맞게 변환
    messages = []
    
    # print(system_instruction)

    # 시스템 메시지 추가
    messages.append(SystemMessage(content=system_instruction))

    # 사용자 질문 메시지 추가
    messages.append(HumanMessage(content=prompt))

    try:
        # LLM 응답 생성
        response = llm.invoke(messages)
        
        # # 답변을 확인해서 '.'이 있는 곳에 '\n' 추가 
        # content = str(response.content)
        # modified_content = content.replace('.', '.\n')
        # print(modified_content)
        # return modified_content  # LLM 응답 내용
        return response.content
    except Exception as e:
        return f"An error occurred while generating a response: {e}"