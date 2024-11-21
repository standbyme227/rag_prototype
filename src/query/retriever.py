from src.embedding.vectorstore_handler import search_vectorstore

def retrieve_relevant_documents(query, top_k=5):
    """
    질의에 대해 가장 유사한 문서를 검색합니다.

    Args:
        query (str): 사용자 질문.
        top_k (int): 검색할 상위 문서 개수.

    Returns:
        list[Document]: 검색된 문서 리스트.
    """
    results = search_vectorstore(query, top_k=top_k)
    if not results:
        print("No relevant documents found.")
        return []

    # 검색 결과 출력
    print(f"Found {len(results)} relevant documents:")
    for result in results:
        print(f"- Source: {result.metadata.get('source', 'Unknown')}, Content: {result.page_content[:100]}...")
    
    return results