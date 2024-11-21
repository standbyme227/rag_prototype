from langchain_community.document_loaders import (
    PyMuPDFLoader, 
    UnstructuredFileLoader, 
    CSVLoader, 
    ImageCaptionLoader,
    WebBaseLoader
)
from langchain.schema import Document
import os
import pytesseract
from PIL import Image
from pdf2image import convert_from_path

# 파일 형식과 로더 매핑
LOADER_MAP = {
    ".pdf": PyMuPDFLoader,
    ".csv": CSVLoader,
    ".png": ImageCaptionLoader,
    ".jpg": ImageCaptionLoader,
    ".jpeg": ImageCaptionLoader,
    ".txt": UnstructuredFileLoader,
    ".docx": UnstructuredFileLoader,
    ".xlsx": UnstructuredFileLoader,
    ".pptx": UnstructuredFileLoader,
    ".md": UnstructuredFileLoader,
    ".odt": UnstructuredFileLoader,
    ".ods": UnstructuredFileLoader,
    ".odp": UnstructuredFileLoader
}

def extract_text_with_ocr(file_path):
    """
    OCR을 사용하여 이미지 또는 PDF 파일의 텍스트를 추출합니다.

    Args:
        file_path (str): OCR 처리를 할 파일 경로.

    Returns:
        str: OCR로 추출한 텍스트.
    """
    extracted_text = ""
    
    # PDF 파일 처리
    if file_path.endswith(".pdf"):
        images = convert_from_path(file_path)
        for image in images:
            extracted_text += pytesseract.image_to_string(image, lang="kor") + "\n"
    
    # 이미지 파일 처리
    elif file_path.endswith((".png", ".jpg", ".jpeg")):
        image = Image.open(file_path)
        extracted_text = pytesseract.image_to_string(image, lang="kor")

    return extracted_text

def get_loader(file_path):
    """
    파일 경로에 따라 적합한 로더 객체를 반환하거나 OCR 처리를 위한 플래그를 반환합니다.

    Args:
        file_path (str): 파일 경로.

    Returns:
        loader: 해당 파일 형식에 맞는 로더 객체 또는 None.
        use_ocr (bool): OCR 처리를 필요로 하는지 여부.
    """
    _, ext = os.path.splitext(file_path)  # 파일 확장자 추출
    ext = ext.lower()  # 확장자를 소문자로 변환

    # 파일 형식에 맞는 로더 반환
    if ext in LOADER_MAP:
        print(f"Loading file with {LOADER_MAP[ext].__name__}: {file_path}")
        try:
            if ext == ".txt":
                return LOADER_MAP[ext](file_path, encoding="utf-8"), False  # 텍스트 파일의 경우 인코딩 지정
            return LOADER_MAP[ext](file_path), False
        except Exception as e:
            print(f"Error initializing loader for {file_path}: {e}")
            return None, False

    # OCR이 필요한 파일 처리
    if ext in [".png", ".jpg", ".jpeg"]:
        print(f"OCR required for: {file_path}")
        return None, True

    print(f"Unsupported file type: {file_path}")
    return None, False

def load_documents(file_paths):
    """
    다양한 파일 형식을 처리하고, Document 객체 리스트를 반환합니다.
    먼저 로더로 처리 후, 필요시 OCR로 처리.

    Args:
        file_paths (list): 처리할 파일 경로 리스트.

    Returns:
        list[Document]: Document 객체 리스트.
    """
    documents = []
    ocr_needed = []

    for file_path in file_paths:
        loader, use_ocr = get_loader(file_path)

        if use_ocr:
            ocr_needed.append(file_path)
            continue

        if not loader:
            continue  # 로더가 없으면 건너뜀

        # 로드 및 Document 리스트에 추가
        try:
            loaded_docs = loader.load()
            
            # 기존 로더로 추출된 텍스트의 길이를 기준으로 OCR 필요 여부 확인
            if (len(" ".join(doc.page_content for doc in loaded_docs).strip()))/len(loaded_docs) < 20:
                print(f"Text from {file_path} is insufficient, adding to OCR queue.")
                ocr_needed.append(file_path)
            else:
                documents.extend(loaded_docs)
                print(f"Loaded {len(loaded_docs)} documents from {file_path}")
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            ocr_needed.append(file_path)

    # OCR로 추가 처리
    for file_path in ocr_needed:
        try:
            ocr_text = extract_text_with_ocr(file_path)
            if ocr_text.strip():  # OCR로 텍스트가 추출되었다면
                documents.append(Document(page_content=ocr_text, metadata={"source": file_path}))
                print(f"OCR processed for {file_path}")
        except Exception as e:
            print(f"Error during OCR processing for {file_path}: {e}")
            
    # print(ocr_needed)

    return documents