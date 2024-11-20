from langchain.document_loaders import (
        PyMuPDFLoader, 
        UnstructuredFileLoader, 
        CSVLoader, 
        # UnstructuredImageLoader, # 이미지를 OCR로 처리하는 로더
        WebBaseLoader, 
        ImageCaptionLoader, # 이미지를 캡션으로 처리하는 로더
    )

from langchain.schema import Document
import os

def load_documents(file_paths):
    """
    다양한 파일 형식을 처리하고, Document 객체 리스트를 반환합니다.

    Args:
        file_paths (list): 처리할 파일 경로 리스트.

    Returns:
        list[Document]: Document 객체 리스트.
    """
    documents = []

    for file_path in file_paths:
        loader = None

        # 파일 형식에 따른 로더 선택
        if file_path.endswith(".pdf"):
            loader = PyMuPDFLoader(file_path)
        elif file_path.endswith(".txt", ".docx", ".xlsx", ".pptx", ".md", ".odt", ".ods", ".odp"):
            loader = UnstructuredFileLoader(file_path, encoding="utf-8")
        elif file_path.endswith(".csv"):
            loader = CSVLoader(file_path)
        elif file_path.endswith((".png", ".jpg", ".jpeg")):
            loader = ImageCaptionLoader(file_path)
        elif file_path.startswith("http"):
            loader = WebBaseLoader(file_path)
        else:
            print(f"Unsupported file type: {file_path}")
            continue

        # 로드 및 Document 리스트에 추가
        try:
            documents.extend(loader.load())
        except Exception as e:
            print(f"Error loading {file_path}: {e}")

    return documents