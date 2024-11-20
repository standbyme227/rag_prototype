from langchain.embeddings.openai import OpenAIEmbeddings

def generate_embeddings(text_chunks):
    embeddings = OpenAIEmbeddings()
    return [embeddings.embed_query(chunk) for chunk in text_chunks]