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

def extract_text_with_ocr(file_path, meta_data=None, lang="kor"):
    """
    OCR을 사용하여 이미지 또는 PDF 파일의 텍스트를 추출합니다.
    현재 'kor' 언어를 사용 중이며, 필요 시 매개변수로 언어 변경 가능.

    Args:
        file_path (str): OCR 처리를 할 파일 경로.

    Returns:
        str: OCR로 추출한 텍스트 (OCR 실패 시 빈 문자열).
    """
    extracted_text_list = []
    page_num = None
    
    if meta_data:
        page_num = meta_data.get("page", None)
    
    try:
        # PDF 파일 처리
        if file_path.lower().endswith(".pdf"):
            images = convert_from_path(file_path)
            count = 0
            for image in images:
                if page_num:
                    if count == page_num:
                        extracted_text_list.append(pytesseract.image_to_string(image, lang=lang))
                        break
                else:
                    extracted_text_list.append(pytesseract.image_to_string(image, lang="kor") + "\n")

        # 이미지 파일 처리
        elif file_path.lower().endswith((".png", ".jpg", ".jpeg")):
            image = Image.open(file_path)
            extracted_text_list.append(pytesseract.image_to_string(image, lang="kor"))

    except Exception as e:
        logging.error(f"Error performing OCR on {file_path}: {e}", exc_info=True)

    return extracted_text_list

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
            
            # 문서를 로드한다.
            # docs를 순환해서 각각의 문서의 상태를 확인한다.
            # 각각의 문서의 글자수를 확인하고 15개 이하라면 해당 페이지는 OCR 처리를 시도한다.
            # OCR 처리가 완료되면 이전 결과와 비교한다.
            # 비교해서 더 나은 결과를 선택한다.
            
            for i in loaded_docs:
                text_len = len(i.page_content)
                meta_data = i.metadata
                
                if text_len < 15:
                    # 전체 문서를 다 하는게 아니라 특정 페이지만을 처리해야한다.
                    ocr_list = extract_text_with_ocr(file_path, meta_data)
                    ocr_text = ocr_list[0] if ocr_list else ""
                    
                    if len(ocr_text) > text_len:
                        i.page_content = ocr_text
            
            documents.extend(loaded_docs)
            logging.info(f"Loaded {len(loaded_docs)} documents from {file_path}")
            
        except Exception as e:
            logging.error(f"Error loading {file_path}: {e}", exc_info=True)
            ocr_needed.append(file_path)

    return documents