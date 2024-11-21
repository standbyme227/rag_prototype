# src/embedding/vectorstore_handler.py
from langchain_chroma import Chroma
from src.embedding.embedder import CustomEmbeddings
from langchain.schema import Document
from src.config import VECTORSTORE_DIR

def get_vectorstore():
    """
    Chroma 인스턴스를 생성하고 반환합니다.
    """
    embedding_function = CustomEmbeddings()
    return Chroma(
        persist_directory=VECTORSTORE_DIR,
        embedding_function=embedding_function
    )

def save_to_vectorstore(chunks, metadata_list):
    """
    텍스트 청크와 메타데이터를 받아 벡터스토어에 저장하기 전에 중복 여부를 확인합니다.
    """
    vectorstore = get_vectorstore()

    # Document 객체 생성
    docs_to_add = []
    for chunk, metadata in zip(chunks, metadata_list):
        # 중복 확인
        results = vectorstore.similarity_search(chunk, k=1)
        if results and results[0].page_content == chunk:
            print(f"Skipping duplicate content: {chunk}")
            continue  # 중복된 데이터는 저장하지 않음
        docs_to_add.append(Document(page_content=chunk, metadata=metadata))
    
    if docs_to_add:
        vectorstore.add_documents(docs_to_add)
        print(f"Added {len(docs_to_add)} documents to vectorstore.")

def remove_from_vectorstore(file_path):
    """
    벡터스토어에서 특정 문서를 제거합니다.
    """
    vectorstore = get_vectorstore()
    
    try:
        vectorstore.delete(
            filter={"path": file_path}  # 메타데이터에서 파일 경로로 삭제 필터링
        )
        print(f"Document removed from vectorstore: {file_path}")
    except Exception as e:
        print(f"Error removing document from vectorstore: {e}")

def search_vectorstore(query, top_k=5):
    """
    벡터스토어에서 쿼리에 대한 유사한 문서를 검색합니다.
    """
    vectorstore = get_vectorstore()
    return vectorstore.similarity_search(query, k=top_k)