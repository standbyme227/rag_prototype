# /src/query/llm_intergration.py

from langchain_community.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage  # Import HumanMessage
from src.query.retriever import retrieve_relevant_documents

def fetch_top_documents(query, top_k=5):
    """
    주어진 질문에 대해 상위 N개의 관련 문서를 검색합니다.

    Args:
        query (str): 사용자의 질문.
        top_k (int): 상위 N개의 문서를 가져옵니다.

    Returns:
        list: 상위 문서 리스트.
    """
    documents = retrieve_relevant_documents(query)
    if not documents:
        print("No relevant documents found.")
        return []
    return documents[:top_k]

def create_prompt(query, context, metadata):
    """
    질문과 문맥을 기반으로 LLM 프롬프트를 생성합니다.

    Args:
        query (str): 사용자의 질문.
        context (str): 문맥 정보.

    Returns:
        str: 생성된 프롬프트.
    """
    if not context:
        return (
            f"I couldn't find any relevant context to answer the question:\n\n"
            f"Question: {query}\n\n"
            f"Please provide a generic response or guidance based on common knowledge."
        )
    return (
        f"Answer the following question based on the provided context:\n\n"
        f"Question: {query}\n\n"
        f"Context:\n{context}\n\n"
        f"Metadata: {metadata}\n\n"
        f"Provide a detailed response based on the context.\n"
        f"Please structure your response clearly with appropriate line breaks for better readability."
    )

def generate_response(query, top_k=5, system_instruction=None):
    """
    질의에 대한 응답을 생성합니다.

    Args:
        query (str): 사용자의 질문.
        top_k (int): 상위 N개의 문서를 사용.
        system_instruction (str, optional): 모델의 동작 지침.

    Returns:
        str: LLM의 응답.
    """
    # LLM 초기화 (ChatOpenAI 사용)
    llm = ChatOpenAI(
        temperature=1, 
        model="gpt-4o-2024-08-06",  # Chat 모델 이름
    )

    # 문서 검색
    top_documents = fetch_top_documents(query, top_k)
    context = "\n".join([doc.page_content for doc in top_documents])
    print(top_documents)
    metadata = top_documents[0].metadata

    # 프롬프트 생성
    prompt = create_prompt(query, context, metadata)
    
    if not system_instruction:
        system_instruction = "Please respond to the following question based on the provided context in Korean."

    # 메시지 포맷에 맞게 변환
    messages = []

    # 시스템 메시지가 있으면 추가
    if system_instruction:
        messages.append(SystemMessage(content=system_instruction))

    # 사용자 질문 메시지 추가
    messages.append(HumanMessage(content=prompt))

    try:
        # LLM 응답 생성
        response = llm.predict_messages(messages)
        
        # # 답변을 확인해서 '.'이 있는 곳에 '\n' 추가 
        # content = str(response.content)
        # modified_content = content.replace('.', '.\n')
        # print(modified_content)
        # return modified_content  # LLM 응답 내용
        return response.content
    except Exception as e:
        return f"An error occurred while generating a response: {e}"