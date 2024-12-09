# /src/preprocessing/splitter.py
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

def split_text(doc: Document, chunk_size: int = 1000, chunk_overlap: int = 200):
    """
    단일 Document 객체를 청킹(Chunking)하여 분리.

    Args:
        doc (Document): LangChain의 Document 객체.
        chunk_size (int): 각 청크의 최대 길이.
        chunk_overlap (int): 청크 간 겹침 길이.

    Returns:
        list[Document]: 분리된 청크들로 구성된 Document 리스트.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    chunks = text_splitter.split_text(doc.page_content)
    split_docs = [
        Document(page_content=chunk, metadata={**doc.metadata, "chunk": i})
        for i, chunk in enumerate(chunks)
    ]

    return split_docs
