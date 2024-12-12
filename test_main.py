from src.preprocessing.new_preprocessor import preprocess_documents
from src.embedding.vectorstore_handler import save_to_vectorstore

# 문서 로딩
# 스플리팅
# 임베딩
# 벡터 저장

# 4단계를 거처 전처리된 문서를 벡터로 저장합니다.
# 저장된 벡터를 테스트합니다. (정확도)

# 작업할 데이터 폴더 경로 (pdf파일들이 존재함)
# 절대 경로 처리
# 대상은 현재 작업폴더 상위에 data 폴더에 존재하는 pdf파일들입니다.
import os
from src.loader.loader import load_documents
path = os.path.abspath('data')
print(path)

# 경로에 존재하는 문서 파일을 순환하며 로딩합니다.
pdf_file_paths = [os.path.join(path, f) for f in os.listdir(path) if f.endswith('.pdf')]

# 일단 테스트니까 그중에 하나만 처리합니다.
# 테스트 대상 : 판결문.pdf
# 테스트 대상 변경 : 디지털 장부 앱 계약서.pdf
# 변경이유 : 판결문은 image로된 pdf라서 ocr처리가 되어야한다.

# 처리해봤는데 한글이어서 그런지 잘 안된다.
# test_path = ''
# for pdf_file_path in pdf_file_paths:
#     if '판결문' in pdf_file_path:
#         test_path = pdf_file_path

test_path = pdf_file_paths[1]
test_path_list = [test_path]

# 기존 코드를 확인하니 documents에는 Document 객체가 있으며
# 속성으로는 page_content, metadata가 있으며, metadata는 source를 가지고있음을 확인함.
# 로더를 확인하니 페이징 처리가 안되어있는걸 확인함.
# OCR을 처리하는 과정에서는 일단 텍스트만 추출해서 그냥 다 합쳐서 처리하는 걸 확인.
# 해당 부분을 수정해야함.

# 파일 형식의 문서를 로드하는 함수
documents = load_documents(test_path_list)

# 문서를 전처리
processed = preprocess_documents(documents)  

contents = [d.page_content for d in processed]
metadatas = [d.metadata for d in processed]

# 전처리된 문서를 벡터화
vertored = save_to_vectorstore(contents, metadatas, is_test_version=True)








