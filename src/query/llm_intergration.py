from langchain.llms import OpenAI
from src.query.retriever import retrieve_relevant_documents

def generate_response(query):
    llm = OpenAI(temperature=0)
    documents = retrieve_relevant_documents(query)
    context = "\n".join([doc.page_content for doc in documents])
    prompt = f"Answer the following question based on the context: {query}\n\nContext:\n{context}"
    response = llm(prompt)
    return response