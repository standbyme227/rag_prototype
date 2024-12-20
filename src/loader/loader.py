# /src/loader/loader.py
import os
import re
import logging
import pytesseract
from urllib.parse import quote
from PIL import Image
from pdf2image import convert_from_path
from utils.ocr import extract_text_with_easyocr_image
from langchain_community.document_loaders import (
    PDFPlumberLoader,
    UnstructuredFileLoader, 
    CSVLoader, 
    ImageCaptionLoader,
)
from langchain.schema import Document
import tempfile
from urllib.parse import quote

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
                        extracted_text_list.append(extract_text_with_easyocr_image(image))
                        # extracted_text_list.append(pytesseract.image_to_string(image, lang=lang))
                        break
                else:
                    extracted_text_list.append(extract_text_with_easyocr_image(image))
                    # extracted_text_list.append(pytesseract.image_to_string(image, lang="kor") + "\n")

        # 이미지 파일 처리
        elif file_path.lower().endswith((".png", ".jpg", ".jpeg")):
            image = Image.open(file_path)
            extracted_text_list.append(extract_text_with_easyocr_image(image))
            # extracted_text_list.append(pytesseract.image_to_string(image, lang="kor"))

    except Exception as e:
        logging.error(f"Error performing OCR on {file_path}: {e}", exc_info=True)

    return extracted_text_list

def get_loader(file):
    """
    파일 객체에 따라 적합한 로더 객체를 반환하거나 OCR 처리를 위한 플래그를 반환합니다.

    Args:
        file (File): 파일 객체

    Returns:
        (loader, use_ocr): 해당 파일 형식에 맞는 로더 객체 또는 None, OCR 필요 여부(bool)
    """
    filename = file.name
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    temp_path = None

    if ext in LOADER_MAP:
        logging.info(f"Loading file with {LOADER_MAP[ext].__name__}: {filename}")
        try:
            # 파일명에서 공백만 언더스코어로 변경
            safe_filename = filename.replace(' ', '_')
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, safe_filename)
            
            with open(temp_path, 'wb') as temp_file:
                temp_file.write(file.read())
                
            if ext == ".txt":
                loader = LOADER_MAP[ext](temp_path, encoding="utf-8")
            else:
                loader = LOADER_MAP[ext](temp_path)
            
            return loader, False
                
        except Exception as e:
            logging.error(f"Error initializing loader for {filename}: {e}", exc_info=True)
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
            return None, False

def remove_page_number(text):
    # 페이지 번호를 표시하는 듯한 문자열을 제거한다.
    # 대부분의 페이지 번호는 특정 줄에 위차하므로, 특정 중에 해당 값이 있는지를 확인하고
    # 만약에 그 값외에 다른 값의 텍스트 수가 10개 이하라면 해당 줄은 페이지 번호로 판단한다.
    # 그리고 해당 줄을 제거한다.
    
    # 각각의 후보군은 다음과 같다. (<number>는 숫자를 의미한다.)
    # 1. <number>/<number>
    # 2. - <number> -
    # 3. page <number>
    # 4. <number> page
    # 5. <number> of <number>
    # 6. <number> 페이지
    # 7. <number> 쪽
    # 8. 페이지 <number> 
    
    # 각각의 후보군을 확인하고, 해당 값이 있는지 확인한다.
    # 만약에 해당 값이 있는 경우, 해당 줄을 위의 조건에 맞는지 확인하고, 맞다면 해당 줄을 제거한다.
    # 코드는 아래와 같다.
    
    # 페이지 번호를 표시하는 가능한 패턴들 정의 (대소문자 구분 안함)
    patterns = [
        r'\d+\s*/\s*\d+',       # 1. <number>/<number>
        r'-\s*\d+\s*-',         # 2. - <number> -
        r'page\s+\d+',          # 3. page <number>
        r'\d+\s+page',          # 4. <number> page
        r'\d+\s+of\s+\d+',      # 5. <number> of <number>
        r'\d+\s*페이지',         # 6. <number> 페이지
        r'\d+\s*쪽',             # 7. <number> 쪽
        r'페이지\s*\d+'          # 8. 페이지 <number>
    ]

    # 패턴을 하나의 정규식으로 합침 (여러 패턴 중 하나라도 매칭되면 True)
    combined_pattern = re.compile('(' + '|'.join(patterns) + ')', re.IGNORECASE)

    text_list = text.split('\n')
    cleaned_lines = []

    for line in text_list:
        # 트림한 라인 기준으로 판단
        stripped_line = line.strip()
        # 토큰 수 확인
        token_count = len(stripped_line.split())

        # 패턴에 매칭되는지 확인
        if token_count <= 10 and combined_pattern.search(stripped_line):
            # 페이지 번호로 추정되는 라인이므로 제거 (append 안함)
            continue
        else:
            # 페이지 번호가 아니면 라인을 그대로 유지
            cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)
        
    

def load_documents(files):
    """
    다양한 파일 형식을 처리하고 Document 객체 리스트를 반환합니다.

    Args:
        files (list): 처리할 파일 객체 리스트

    Returns:
        list[Document]: Document 객체 리스트
    """
    documents = []

    for file in files:
        loader, use_ocr = get_loader(file)
        file_path = loader.file_path

        if not loader:
            continue

        try:
            loaded_docs = loader.load()
            
            ocr_list = []
            
            for idx, doc in enumerate(loaded_docs):
                result = doc.page_content
                text_len = len(result)
                meta_data = doc.metadata
                
                if text_len < 15:
                    if not ocr_list:
                        ocr_list = extract_text_with_ocr(file_path, meta_data)

                    if ocr_list:
                        ocr_text = ocr_list[idx]
                    else:
                        ocr_text = ""
                        
                    if len(ocr_text) > text_len:
                        result = ocr_text
                
                result = remove_page_number(result)
                doc.page_content = result
            
            documents.extend(loaded_docs)
            logging.info(f"Loaded {len(loaded_docs)} documents from {file.name}")
            
        except Exception as e:
            raise e

    return documents