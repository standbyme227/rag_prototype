import os
import numpy as np
from PIL import Image
import pytesseract
import easyocr
from easyocr import Reader
from pdf2image import convert_from_path

def extract_text_with_tesseract(file_path, lang=None):
    """
    Tesseract OCR을 사용하여 텍스트를 추출합니다.

    Args:
        file_path (str): OCR 처리를 할 파일 경로.
        lang (str): Tesseract 언어 설정 (기본값: "eng").

    Returns:
        str: OCR로 추출한 텍스트.
    """
    if lang is None:
        lang = "slk"
    extracted_text = ""
    
    # PDF 파일 처리
    if file_path.endswith(".pdf"):
        images = convert_from_path(file_path)
        for image in images:
            extracted_text += pytesseract.image_to_string(image, lang=lang) + "\n"
    
    # 이미지 파일 처리
    elif file_path.endswith((".png", ".jpg", ".jpeg")):
        image = Image.open(file_path)
        extracted_text = pytesseract.image_to_string(image, lang=lang)

    return extracted_text


def extract_text_with_easyocr(file_path, lang_list=None):
    """
    EasyOCR을 사용하여 텍스트를 추출합니다.

    Args:
        file_path (str): OCR 처리를 할 파일 경로.
        lang_list (list): EasyOCR 언어 리스트 (기본값: ["en"]).

    Returns:
        str: OCR로 추출한 텍스트.
    """
    if lang_list is None:
        # lang_list = ["sk"]  # 기본 언어 설정
        lang_list = ["ko"]

    reader = easyocr.Reader(lang_list)
    extracted_text = ""

    # PDF 파일 처리
    if file_path.endswith(".pdf"):
        images = convert_from_path(file_path)
        for image in images:
            text = reader.readtext(image, detail=0)  # detail=0으로 간단한 텍스트만 가져옴
            extracted_text += " ".join(text) + "\n"
    
    # 이미지 파일 처리
    elif file_path.endswith((".png", ".jpg", ".jpeg")):
        text = reader.readtext(file_path, detail=0)
        extracted_text = " ".join(text)

    return extracted_text

def extract_text_with_easyocr_image(image):
    reader = Reader(['ko', 'en'], gpu=True)

    # Pillow 이미지라면 numpy array로 변환
    if isinstance(image, Image.Image):
        image = np.array(image)

    # EasyOCR에서 지원하지 않는 형식이면 에러 발생
    if not isinstance(image, (np.ndarray, str, bytes)):
        raise ValueError("Invalid input type for EasyOCR. Must be numpy array, string, or bytes.")

    # OCR 실행
    text = reader.readtext(image, detail=0)
    extracted_text = " ".join(text)
    return extracted_text


def extract_text_with_ocr(file_path, ocr_engine="tesseract", lang=None, lang_list=None):
    """
    OCR 엔진을 선택하여 텍스트를 추출합니다.

    Args:
        file_path (str): OCR 처리를 할 파일 경로.
        ocr_engine (str): 사용할 OCR 엔진 ("tesseract" 또는 "easyocr").
        lang (str): Tesseract 언어 설정 (기본값: "eng").
        lang_list (list): EasyOCR 언어 리스트 (기본값: ["en"]).

    Returns:
        str: OCR로 추출한 텍스트.
    """
    if ocr_engine == "tesseract":
        return extract_text_with_tesseract(file_path, lang=lang)
    elif ocr_engine == "easyocr":
        return extract_text_with_easyocr(file_path, lang_list=lang_list)
    else:
        raise ValueError(f"Unsupported OCR engine: {ocr_engine}")
    

def process_images_in_directory(directory_path, ocr_engine="tesseract", lang=None, lang_list=None):
    """
    디렉토리 내 이미지 파일들을 OCR 처리한 후 결과를 하나의 텍스트 파일로 저장합니다.

    Args:
        directory_path (str): 이미지 파일들이 저장된 디렉토리 경로.
        ocr_engine (str): 사용할 OCR 엔진 ("tesseract" 또는 "easyocr").
        lang (str): Tesseract 언어 설정 (기본값: "eng").
        lang_list (list): EasyOCR 언어 리스트 (기본값: ["en"]).

    Returns:
        str: 생성된 텍스트 파일 경로.
    """
    if not os.path.isdir(directory_path):
        raise ValueError("The provided path is not a valid directory.")

    # 폴더 이름을 기반으로 결과 파일 이름 생성
    folder_name = os.path.basename(os.path.normpath(directory_path))
    results_dir = os.path.join(directory_path, "results")
    os.makedirs(results_dir, exist_ok=True)
    output_file_path = os.path.join(results_dir, f"{folder_name}_{ocr_engine}_results.txt")

    # OCR 처리할 이미지 파일 확장자
    image_extensions = (".png", ".jpg", ".jpeg")
    image_files = [f for f in os.listdir(directory_path) if f.endswith(image_extensions)]

    if not image_files:
        raise ValueError("No image files found in the directory.")

    # OCR 처리 및 결과 저장
    from utils.ocr import extract_text_with_ocr
    count = 0
    with open(output_file_path, "w", encoding="utf-8") as output_file:
        for image_file in image_files:
            count += 1
            print(f"Processing image {count}/{len(image_files)}: {image_file}")
            image_path = os.path.join(directory_path, image_file)
            extracted_text = extract_text_with_ocr(image_path, ocr_engine=ocr_engine, lang=lang, lang_list=lang_list)
            output_file.write(f"Results for {image_file}:\n")
            output_file.write(extracted_text + "\n\n")
            print(">>>>> Processing complete.")

    return output_file_path