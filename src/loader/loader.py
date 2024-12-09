# /src/loader/loader.py
import os
import logging
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
from langchain_community.document_loaders import (
    PDFPlumberLoader,
    UnstructuredFileLoader, 
    CSVLoader, 
    ImageCaptionLoader,
)
from langchain.schema import Document

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# 파일 형식과 로더 매핑
LOADER_MAP = {
    ".pdf": PDFPlumberLoader,
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
    현재 'kor' 언어를 사용 중이며, 필요 시 매개변수로 언어 변경 가능.

    Args:
        file_path (str): OCR 처리를 할 파일 경로.

    Returns:
        str: OCR로 추출한 텍스트 (OCR 실패 시 빈 문자열).
    """
    extracted_text = ""
    try:
        # PDF 파일 처리
        if file_path.lower().endswith(".pdf"):
            images = convert_from_path(file_path)
            for image in images:
                extracted_text += pytesseract.image_to_string(image, lang="kor") + "\n"

        # 이미지 파일 처리
        elif file_path.lower().endswith((".png", ".jpg", ".jpeg")):
            image = Image.open(file_path)
            extracted_text = pytesseract.image_to_string(image, lang="kor")

    except Exception as e:
        logging.error(f"Error performing OCR on {file_path}: {e}", exc_info=True)

    return extracted_text

def get_loader(file_path):
    """
    파일 경로에 따라 적합한 로더 객체를 반환하거나 OCR 처리를 위한 플래그를 반환합니다.

    Args:
        file_path (str): 파일 경로.

    Returns:
        (loader, use_ocr): 해당 파일 형식에 맞는 로더 객체 또는 None, OCR 필요 여부(bool).
    """
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    # 파일 형식에 맞는 로더 반환
    if ext in LOADER_MAP:
        logging.info(f"Loading file with {LOADER_MAP[ext].__name__}: {file_path}")
        try:
            if ext == ".txt":
                return LOADER_MAP[ext](file_path, encoding="utf-8"), False  # 텍스트 파일의 경우 인코딩 지정
            return LOADER_MAP[ext](file_path), False
        except Exception as e:
            logging.error(f"Error initializing loader for {file_path}: {e}", exc_info=True)
            return None, False

    # OCR이 필요한 이미지 형식 처리
    if ext in [".png", ".jpg", ".jpeg"]:
        logging.info(f"OCR required for: {file_path}")
        return None, True

    # 지원하지 않는 파일 형식
    logging.warning(f"Unsupported file type: {file_path}")
    return None, False

def load_documents(file_paths):
    """
    다양한 파일 형식을 처리하고 Document 객체 리스트를 반환합니다.
    1) 로더를 통해 텍스트 추출 시도
    2) 텍스트가 충분치 않으면 OCR 시도
    3) 최종적으로 Document 리스트 반환

    Args:
        file_paths (list): 처리할 파일 경로 리스트.

    Returns:
        list[Document]: Document 객체 리스트.
    """
    documents = []
    ocr_needed = []

    for file_path in file_paths:
        loader, use_ocr = get_loader(file_path)

        # OCR 필요 표시된 파일은 OCR 처리 목록에 추가
        if use_ocr:
            ocr_needed.append(file_path)
            continue

        if not loader:
            # 로더가 없으면 해당 파일은 건너뜀
            continue

        # 로더를 통해 문서 로딩
        try:
            loaded_docs = loader.load()
            
            # 평균 텍스트 길이를 기준으로 OCR 필요성 판단
            # 아래 조건은 문서의 평균 텍스트 길이가 매우 짧은 경우(OCR 필요성 가정) OCR 큐에 추가하는 로직
            all_text = " ".join(doc.page_content for doc in loaded_docs).strip()
            avg_text_len = len(all_text)/len(loaded_docs) if loaded_docs else 0
            
            # print(all_text)

            # 기준(20자)보다 적다면 OCR을 통한 재추출 시도
            if avg_text_len < 20:
                logging.info(f"Text from {file_path} is insufficient (avg length < 20), adding to OCR queue.")
                ocr_needed.append(file_path)
            else:
                documents.extend(loaded_docs)
                logging.info(f"Loaded {len(loaded_docs)} documents from {file_path}")
        except Exception as e:
            logging.error(f"Error loading {file_path}: {e}", exc_info=True)
            ocr_needed.append(file_path)

    # OCR 처리
    for file_path in ocr_needed:
        try:
            ocr_text = extract_text_with_ocr(file_path)
            if ocr_text.strip():
                # OCR 결과가 비어있지 않다면 문서 추가
                documents.append(Document(page_content=ocr_text, metadata={"source": file_path}))
                logging.info(f"OCR processed for {file_path}")
            else:
                logging.warning(f"OCR did not extract any text from {file_path}. Skipping.")
        except Exception as e:
            logging.error(f"Error during OCR processing for {file_path}: {e}", exc_info=True)

    return documents