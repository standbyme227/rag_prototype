# src/embedding/embedder.py
from langchain_openai import OpenAIEmbeddings


class CustomEmbeddings(OpenAIEmbeddings):
    def embed_documents(self, texts):
        # 커스텀 로직을 추가하거나 기존 메소드를 호출합니다.
        return super().embed_documents(texts)
    
    def embed_query(self, text):
        # 커스텀 로직을 추가하거나 기존 메소드를 호출합니다.
        return super().embed_query(text)