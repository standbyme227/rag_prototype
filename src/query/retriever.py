from src.embedding.vectorstore_handler import search_vectorstore

def retrieve_relevant_documents(query):
    results = search_vectorstore(query)
    for result in results:
        print(f"Document: {result.metadata}, Content: {result.page_content}")
    return results