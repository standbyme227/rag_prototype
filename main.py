import json
import os
import uuid
import streamlit as st
from src.query.llm_intergration import generate_response
from src.config import DATA_DIR
from src.embedding.vectorstore_handler import remove_from_vectorstore
from src.preprocessing.metadata_manager import generate_doc_id

# file_list.json 경로
FILE_LIST_PATH = os.path.join(DATA_DIR, "file_list.json")

# 파일 목록 로드
def load_file_list():
    if os.path.exists(FILE_LIST_PATH):
        with open(FILE_LIST_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

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
            remove_from_vectorstore(file_path=file_to_remove.get("filepath"), remove_all_versions=True)
        
        file_list = [f for f in file_list if f.get("id") != file_id]
        save_file_list(file_list)
        st.success("파일이 삭제되었습니다.")
    else:
        st.warning("해당 파일을 찾을 수 없습니다.")

# 업로드된 파일을 목록에 추가
def add_uploaded_file_to_list(file):
    file_list = load_file_list()
    file_path = os.path.join(DATA_DIR, file.name)
    
    # 파일 저장
    with open(file_path, "wb") as f:
        f.write(file.read())
    
    doc_id = generate_doc_id(file_path)
    file_entry = {
        "id": str(uuid.uuid4()),
        "filename": file.name,
        "filepath": file_path,
        "doc_id": doc_id,
        "metadata": {}
    }
    file_list.append(file_entry)
    save_file_list(file_list)
    st.success(f"파일 {file.name} 이(가) 업로드되고 목록에 추가되었습니다.")

# 공통 화면: 파일 목록 및 검색/삭제 처리
def display_file_list():
    with st.expander("Stored Documents and Search", expanded=False):
        search_query = st.text_input("Search in file list:", key="search_query")

        file_list = load_file_list()
        if search_query.strip():
            filtered_files = [f for f in file_list if search_query.lower() in f.get("filename", "").lower()]
        else:
            filtered_files = file_list

        if not filtered_files:
            st.info("No files found.")
        else:
            if "delete_confirm" not in st.session_state:
                st.session_state.delete_confirm = None

            for f in filtered_files:
                filename = f.get("filename", "No Name")
                file_id = f.get("id")
                
                file_col1, file_col2 = st.columns([9, 1])
                with file_col1:
                    st.write(filename)
                with file_col2:
                    if st.button("❌", key=file_id):
                        st.session_state.delete_confirm = file_id

                # 삭제 확인
                if st.session_state.delete_confirm == file_id:
                    st.warning(f"정말로 {filename}을(를) 삭제하시겠습니까?")
                    confirm_col1, confirm_col2 = st.columns([1, 1])
                    with confirm_col1:
                        if st.button("Yes", key=f"yes_{file_id}"):
                            remove_file_entry(file_id)
                            st.session_state.delete_confirm = None
                    with confirm_col2:
                        if st.button("No", key=f"no_{file_id}"):
                            st.session_state.delete_confirm = None

# Search 탭: Q&A 인터페이스
def display_search_tab():
    st.header("Search for stored documents")
    
    # 채팅 기록 초기화
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []  # ('role', 'message') 형식의 튜플 리스트

    # 검색 결과 수 옵션 (세션 상태 초기화)
    if 'top_k' not in st.session_state:
        st.session_state.top_k = 5  # 기본값 설정

    # 사용자 입력 텍스트 상태 초기화
    if 'query_text' not in st.session_state:
        st.session_state.query_text = ""  # 사용자 입력 텍스트

    # 채팅 메시지 표시
    # 스크롤 가능한 컨테이너로 대화 영역 생성
    with st.container(height=500):
        for role, message in st.session_state.chat_history:
            with st.chat_message(role):
                formatted_message = format_message(message)
                st.markdown(formatted_message, unsafe_allow_html=True)

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
    query = st.text_area(
        "Enter your question:",
        placeholder="Ask about your documents...",
        key="query_text",
        on_change=execute_query,  # 콜백 함수 등록
        label_visibility='collapsed'
    )

    # 검색 결과 수 옵션 (접을 수 있는 설정)
    with st.expander("Advanced Options", expanded=False):
        st.session_state.top_k = st.slider(
            "Number of documents to retrieve:",
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
    tab1, tab2 = st.tabs(["Home", "Search"])
    with tab1:
        st.header("Home")
        uploaded_files = st.file_uploader("Upload files", accept_multiple_files=True, key="file_uploader", label_visibility='collapsed')
        if uploaded_files:
            for uploaded_file in uploaded_files:
                add_uploaded_file_to_list(uploaded_file)
    with tab2:
        display_search_tab()

if __name__ == "__main__":
    main()