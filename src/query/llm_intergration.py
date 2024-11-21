from langchain_community.llms import OpenAI
from src.query.retriever import retrieve_relevant_documents

def generate_response(query, top_k=3):
    """
    질의에 대한 응답을 생성합니다.

    Args:
        query (str): 사용자의 질문.
        top_k (int): 상위 N개의 문서를 사용.

    Returns:
        str: LLM의 응답.
    """
    llm = OpenAI(temperature=0)
    
    # 문서 검색
    documents = retrieve_relevant_documents(query)
    top_documents = documents[:top_k]  # 상위 N개 문서 선택

    # 문맥 생성
    context = "\n".join([doc.page_content for doc in top_documents])
    if not context:
        return "Sorry, I couldn't find relevant information to answer your question."
    
    print(f"Query: {query}, Context: {context}")

    # 프롬프트 생성
    prompt = (
        f"Answer the following question based on the provided context:\n\n"
        f"Question: {query}\n\n"
        f"Context:\n{context}\n\n"
        f"Provide a detailed response based on the context."
    )
    
    # LLM 응답 생성
    try:
        response = llm(prompt)
    except Exception as e:
        response = f"An error occurred while generating a response: {e}"

    print("대답완료")
    return response