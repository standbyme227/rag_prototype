import json
import os
import streamlit as st
import re
from src.config import DATA_DIR
from src.query.llm_intergration import generate_response
from src.loader.loader import load_documents
from src.embedding.vectorstore_handler import (
    save_to_vectorstore,
    remove_from_vectorstore, 
    get_vectorstore,
)
from src.preprocessing import (
    generate_doc_id,
    preprocess_documents,
)
import unicodedata

def normalize_string(s):
    return unicodedata.normalize('NFC', s)

# file_list.json 경로
FILE_LIST_PATH = os.path.join(DATA_DIR, "file_list.json")

def save_data(file_path):
    path_list = [file_path]
    
    # 파일 형식의 문서를 로드하는 함수
    documents = load_documents(path_list)

    # 문서를 전처리
    processed = preprocess_documents(documents)  

    contents = [d.page_content for d in processed]
    metadatas = [d.metadata for d in processed]

    # 전처리된 문서를 벡터화
    save_to_vectorstore(contents, metadatas, is_test_version=True)
    
    # 벡터스토어에서 데이터를 확인
    vectorstore = get_vectorstore(is_test_version=True)
    metadatas = vectorstore.get()['metadatas']
    print(metadatas)
    
    return metadatas

def set_file_list_data(metadata):
    file_name = metadata.get('file_name', "Unknown")
    doc_id = metadata.get('doc_id', "")
    return {
        "doc_id": doc_id,
        "filename": file_name,
    }

def create_file_list():
    vectorstore = get_vectorstore(is_test_version=True)
    
    # 벡터스토어에서 데이터를 확인
    all_docs = vectorstore.get()['metadatas']
    unique_docs = []
    unique_doc_ids = []
    
    for doc in all_docs:
        doc_id = doc.get('doc_id')
        if doc_id not in unique_doc_ids:
            unique_docs.append(doc)
            unique_doc_ids.append(doc_id)
    
    # 파일 목록 구성
    file_list = []
    for doc in unique_docs:
        result = set_file_list_data(doc)
        file_list.append(result)
    
    return file_list    

# 파일 목록 로드
def load_file_list():
    if os.path.exists(FILE_LIST_PATH):
        with open(FILE_LIST_PATH, 'r', encoding='utf-8') as f:
            file_list = json.load(f)
            
            if not isinstance(file_list, list):
                raise ValueError("file_list.json should contain a list of file entries.")
    else:
        # 파일이 없으면 하나 생성한다.
        # 벡터스토어에서 데이터를 확인한 뒤, 해당 데이터들을 순환하면서 doc_id가 겹치는 경우는 삭제해서
        # 각각 unique한 doc_id를 갖는 데이터만 남긴다.
        # 그리고 그 데이터들을 순환하며 metadata를 확인하고
        # 그 metadata에서 path와 doc_id를 추출해서 해당 템플릿에 맞춰 file_list를 구성한다.
        # 구성된 file_list를 저장한다.
        
        file_list = create_file_list()
        save_file_list(file_list)
        
    return file_list

# 파일 목록 저장
def save_file_list(file_list):
    with open(FILE_LIST_PATH, 'w', encoding='utf-8') as f:
        json.dump(file_list, f, ensure_ascii=False, indent=4)

# 파일 삭제 처리
def remove_file_entry(file_id):
    file_list = load_file_list()
    file_to_remove = None

    for f in file_list:
        if f.get("id") == file_id:
            file_to_remove = f
            break

    if file_to_remove:
        doc_id = file_to_remove.get("doc_id")
        if doc_id:
            remove_from_vectorstore(file_path=file_to_remove.get("path"), remove_all_versions=True)
        
        file_list = [f for f in file_list if f.get("id") != file_id]
        save_file_list(file_list)
        st.success("파일이 삭제되었습니다.")
    else:
        st.warning("해당 파일을 찾을 수 없습니다.")

# 업로드된 파일을 목록에 추가
def add_uploaded_file_to_list(file):
    file_list = load_file_list()
    file_path = os.path.join(DATA_DIR, file.name)
    
    # 파일 저장 -> 벡터스토어에 추가로 변경
    # with open(file_path, "wb") as f:
    #     f.write(file.read())
    metadatas = save_data(file_path)
    
    new_file_list = []
    
    for metadata in metadatas:
        result = set_file_list_data(metadata)
        # 이미 파일 목록에 있는지 확인
        if result:
            # doc_id를 비교한다.
            doc_id = result.get("doc_id")
            if doc_id in [f.get("doc_id") for f in file_list]:
                st.warning(f"파일 {result.get('filename')}은(는) 이미 업로드되었습니다.")
                continue
            else:
                new_file_list.append(result)

    existing_doc_ids = [f.get("doc_id") for f in file_list]
    for f in new_file_list:
        doc_id = f.get("doc_id")
        # 기존의 파일리스트에 해당하는 doc_id가 있는지 확인
        if doc_id in existing_doc_ids:
            st.warning(f"파일 {f.get('filename')}은(는) 이미 업로드되었습니다.")
            continue
        else:
            file_list.append(f)
    
    save_file_list(file_list)
    st.success(f"파일 {file.name} 이(가) 업로드되고 목록에 추가되었습니다.")

def normalize_string(text):
    return re.sub(r'[^a-zA-Z0-9가-힣]', '', text)

def display_file_list():
    # Expander 상태 초기화
    if "expander_open" not in st.session_state:
        st.session_state["expander_open"] = False

    # Expander 열림 여부에 따라 파일 리스트 업데이트
    with st.expander("**Stored Documents 📄 and Search 🔍**", expanded=st.session_state["expander_open"]):
        # Expander가 열리거나 닫힐 때 refresh 트리거
        current_state = st.session_state["expander_open"]
        new_state = not current_state  # 토글 상태 계산

        if current_state != new_state:  # 상태 변화 확인
            st.session_state["expander_open"] = new_state
            file_list = load_file_list()  # 최신 파일 리스트 로드
            
        # 검색창 영역
        search_col1, search_col2 = st.columns([3, 3])
        with search_col1:
            search_query = st.text_input(
                "Search in file list:",
                key="search_query",
                placeholder="Type to filter documents..."
            )

        # 파일 리스트 영역
        file_list = load_file_list()
        if search_query.strip():
            search_query_normalized = normalize_string(search_query.lower())
            filtered_files = [
                f for f in file_list
                if search_query_normalized in normalize_string(f.get("filename", "").lower())
            ]
        else:
            filtered_files = file_list

        if not filtered_files:
            st.info("No files found.")
        else:
            # 파일 리스트 출력
            with st.container(height=200):
                st.markdown("""
                <style>
                .file-item:hover {
                    background-color: #f0f0f0;
                    cursor: pointer;
                }
                .file-item {
                    padding: 7px 10px;
                    border-bottom: 1px solid #e0e0e0;
                }
                </style>
                """, unsafe_allow_html=True)

                for f in filtered_files:
                    filename = f.get("filename", "No Name")
                    file_id = f.get("doc_id")

                    file_col1, file_col2 = st.columns([9, 1])
                    with file_col1:
                        st.markdown(f"<div class='file-item'>{filename}</div>", unsafe_allow_html=True)
                    with file_col2:
                        # 버튼 클릭 시 상태 설정
                        if st.button("❌", key=f"delete_button_{file_id}", help="Delete this file"):
                            st.session_state.delete_confirm = file_id

                # 삭제 확인
                if "delete_confirm" in st.session_state and st.session_state.delete_confirm:
                    file_to_delete = next(
                        (f for f in filtered_files if f.get("doc_id") == st.session_state.delete_confirm), None
                    )
                    if file_to_delete:
                        filename = file_to_delete.get("filename", "No Name")
                        validation_co1, validation_col2 = st.columns([1, 1])
                        with validation_co1:
                            st.warning(f"정말로 {filename}을(를) 삭제하시겠습니까?")
                        with validation_col2:
                            confirm_col1, confirm_col2 = st.columns([1, 1])
                            with confirm_col1:
                                if st.button("Yes", key=f"yes_confirm_{st.session_state.delete_confirm}"):
                                    remove_file_entry(st.session_state.delete_confirm)
                                    st.session_state.delete_confirm = None
                                    st.rerun()  # 화면 재실행
                            with confirm_col2:
                                if st.button("No", key=f"no_confirm_{st.session_state.delete_confirm}"):
                                    st.session_state.delete_confirm = None
                                    st.rerun()  # 화면 재실행

    # 상태 트리거 기반 재실행
    if "refresh" not in st.session_state:
        st.session_state["refresh"] = False

# Search 탭: Q&A 인터페이스
def display_search_tab():
    st.subheader("Search for stored documents 🔍")
    
    # 채팅 기록 초기화
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []  # ('role', 'message') 형식의 튜플 리스트

    # 검색 결과 수 옵션 (세션 상태 초기화)
    if 'top_k' not in st.session_state:
        st.session_state.top_k = 5  # 기본값 설정

    # 사용자 입력 텍스트 상태 초기화
    if 'query_text' not in st.session_state:
        st.session_state.query_text = ""  # 사용자 입력 텍스트

    # 채팅 영역과 입력 영역을 7:3 비율로 배치
    chat_col, input_col = st.columns([7, 3])
    
    with chat_col:
        # 스크롤 가능한 컨테이너로 대화 영역 생성
        with st.container(height=500):
            for role, message in st.session_state.chat_history:
                with st.chat_message(role):
                    formatted_message = format_message(message)
                    st.markdown(formatted_message, unsafe_allow_html=True)

    with input_col:
        # 사용자 질의 입력 (콜백 함수 설정)
        def execute_query():
            query = st.session_state.query_text.strip()
            if query:
                # 사용자 메시지 추가
                st.session_state.chat_history.append(("user", query))
                
                # 검색 및 응답 생성
                response = generate_response(query, top_k=st.session_state.top_k, is_test_version=True, max_tokens=None)
                
                # 봇 응답 추가
                st.session_state.chat_history.append(("bot", response))
                
                # 입력 텍스트 초기화
                st.session_state.query_text = ""

        # 사용자 입력 영역
        st.text_area(
            "Enter your question:",
            placeholder="Ask about your documents...",
            key="query_text",
            on_change=execute_query,  # 콜백 함수 등록
            label_visibility='collapsed',
            height=330
        )

        # 검색 결과 수 옵션 (접을 수 있는 설정)
        with st.expander("**Advanced Options**", expanded=False):
            st.session_state.top_k = st.slider(
                "Choose the number of top relevant documents to retrieve:",
                min_value=1,
                max_value=20,
                value=st.session_state.top_k,  # 초기값을 세션 상태에서 가져옴
                key="top_k_slider"
            )

def format_message(message):
    """
    메시지의 Markdown 구조를 개선하여 줄바꿈과 강조를 처리.
    """
    return message.replace("\n", "  \n")

# Main Function
def main():
    st.set_page_config(layout="wide")
    st.title("Standard RAG System")

    # 공통 화면
    display_file_list()

    # 탭 구성
    tab1, tab2 = st.tabs(["**Home**", "**Search**"])
    with tab1:
        st.subheader("Home 🏠")
        uploaded_files = st.file_uploader("Upload files", accept_multiple_files=True, key="file_uploader", label_visibility='collapsed')
        if uploaded_files:
            for uploaded_file in uploaded_files:
                add_uploaded_file_to_list(uploaded_file)
    with tab2:
        display_search_tab()

if __name__ == "__main__":
    main()