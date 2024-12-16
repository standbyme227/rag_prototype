import json
import os
import streamlit as st
import re
import unicodedata
from src.config import DATA_DIR, VECTORSTORE_VERSION
from src.query.llm_intergration import generate_response
from src.loader.loader import load_documents
from src.embedding.vectorstore_handler import (
    save_to_vectorstore,
    remove_from_vectorstore, 
    VectorStoreManager,
)
from src.preprocessing import (
    generate_doc_id,
    preprocess_documents,
)

from utils.file_manager import FileManager

# file_list.json 경로
FILE_LIST_PATH = os.path.join(DATA_DIR, "file_list.json")

file_manager = FileManager(FILE_LIST_PATH)

vectorstore = VectorStoreManager.get_instance()


# 업로드된 파일을 목록에 추가
def add_uploaded_file_to_list(file):
    if not st.session_state.file_uploaded:
        file_list = file_manager.load_file_list()
        file_path = os.path.join(DATA_DIR, file.name)
        
        # 벡터스토어에서 중복 체크
        doc_id = generate_doc_id(file_path)
        existing_docs = vectorstore._collection.get(
            where={"doc_id": doc_id}
        )
        
        if existing_docs and existing_docs.get('documents'):
            return []
        
        metadatas = save_data(file)
        new_file_list = []
        
        unique_metadatas, _ = file_manager._get_unique_metadatas()
        
        for metadata in unique_metadatas:
            result = file_manager._set_file_metadata(metadata)
            if result and result.get("doc_id") not in [f.get("doc_id") for f in file_list]:
                new_file_list.append(result)

        if new_file_list:
            file_list.extend(new_file_list)
            file_manager.save_file_list(file_list)
            st.success(f"파일 {file.name} 이(가) 업로드되고 목록에 추가되었습니다.")
            st.rerun()
        
        st.session_state.file_uploaded = True
    else:
        st.session_state.file_uploaded = False

def normalize_string(s):
    return unicodedata.normalize('NFC', s)

def save_data(file):
    # path_list = [file_path]
    file_list = [file]
    
    # 파일 형식의 문서를 로드하는 함수
    documents = load_documents(file_list)

    # 문서를 전처리
    processed = preprocess_documents(documents)  

    contents = [d.page_content for d in processed]
    metadatas = [d.metadata for d in processed]

    # 전처리된 문서를 벡터화
    save_to_vectorstore(contents, metadatas, vectorstore_version=VECTORSTORE_VERSION)
    
    # 벡터스토어에서 데이터를 확인
    all_metadatas = vectorstore.get()['metadatas']
    print(all_metadatas)
    
    return metadatas

def normalize_string(text):
    return re.sub(r'[^a-zA-Z0-9가-힣]', '', text)

def display_file_list():
    # Expander 상태 초기화
    if "expander_open" not in st.session_state:
        st.session_state["expander_open"] = False

    # Expander를 열고 닫을 때만 상태를 변경하도록 수정
    with st.expander("**Stored Documents 📄 and Search 🔍**", expanded=st.session_state["expander_open"]) as expander:
        if expander:  # expander가 클릭되었을 때만 상태 변경
            st.session_state["expander_open"] = not st.session_state["expander_open"]
            
        # 파일 리스트
        file_list = file_manager.load_file_list()
        # 검색창 영역
        search_col1, search_col2 = st.columns([3, 3])
        with search_col1:
            search_query = st.text_input(
                "Search in file list:",
                key="search_query",
                placeholder="Type to filter documents..."
            )

        # 파일 리스트 영역
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
            with st.container(height=230):
                st.markdown("""
                <style>
                .file-item:hover {
                    background-color: #f0f0f0;
                    cursor: pointer;
                }
                .file-item {
                    padding: 7px 10px;
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
                        if st.button("❌", key=f"delete_button_{file_id}", help="Delete this file"):
                            st.session_state.delete_confirm = file_id
                    
                    # 삭제 확인 메시지를 해당 파일 바로 아래에 표시
                    if "delete_confirm" in st.session_state and st.session_state.delete_confirm == file_id:
                        confirm_col1, confirm_col2, confirm_col3 = st.columns([6, 1, 1])
                        with confirm_col1:
                            st.warning(f"정말로 {filename}을(를) 삭제하시겠습니까?")
                        with confirm_col2:
                            if st.button("Yes", key=f"yes_confirm_{file_id}", use_container_width=True):
                                file_manager.remove_file(file_id)
                                st.session_state.delete_confirm = None
                                st.rerun()
                        with confirm_col3:
                            if st.button("No", key=f"no_confirm_{file_id}", use_container_width=True):
                                st.session_state.delete_confirm = None
                                st.rerun()

    # 상태 트리거 기반 재실행
    if "refresh" not in st.session_state:
        st.session_state["refresh"] = False

# Search 탭: Q&A 인터페이스
def display_search_tab():
    st.subheader("Search for stored documents 🔍")
    
    st.markdown("""
        <style>
        .stChatInput {
            height: 330px;
            width: 100%;
        }
        
        .stChatInput > div {
            height: 100%;
        }
        
        .stChatInput textarea {
            height: 330px !important;
            resize: none;
        }
        </style>
    """, unsafe_allow_html=True)
    
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'top_k' not in st.session_state:
        # 기본적으로 15로 지정, 나중에 reranker를 처리하고 나서 줄인다.
        st.session_state.top_k = 15
    if 'processing' not in st.session_state:
        st.session_state.processing = False
    if 'last_user_input' not in st.session_state:  # 마지막 사용자 입력 저장용
        st.session_state.last_user_input = None

    chat_col, input_col = st.columns([7, 3])
    
    with chat_col:
        with st.container(height=500):
            for role, message in st.session_state.chat_history:
                with st.chat_message(role):
                    formatted_message = format_message(message)
                    st.markdown(formatted_message, unsafe_allow_html=True)
            
            if st.session_state.processing:
                with st.spinner('답변을 생성하는 중입니다...'):
                    st.empty()

    with input_col:
        if prompt := st.chat_input("Ask about your documents..."):
            if not st.session_state.processing:
                # 사용자 메시지 추가
                st.session_state.chat_history.append(("user", prompt))
                st.session_state.last_user_input = prompt  # 입력 저장
                st.session_state.processing = True
                st.rerun()
                
        # processing 상태일 때 응답 생성
        if st.session_state.processing and st.session_state.last_user_input:
            # 응답 생성
            response = generate_response(
                st.session_state.last_user_input,  # 저장된 입력 사용
                top_k=st.session_state.top_k,
                vectorstore_version=VECTORSTORE_VERSION,
                max_tokens=None
            )
            
            # 봇 응답 추가
            st.session_state.chat_history.append(("bot", response))
            st.session_state.processing = False
            st.session_state.last_user_input = None  # 입력 초기화
            st.rerun()

        with st.expander("**Advanced Options**", expanded=False):
            st.session_state.top_k = st.slider(
                "Choose the number of top relevant documents to retrieve:",
                min_value=1,
                max_value=20,
                value=st.session_state.top_k,
                key="top_k_slider"
            )

def format_message(message):
    """
    메시지의 Markdown 구조를 개선하여 줄바꿈과 강조를 처리.
    """
    return message.replace("\n", "  \n")

# Main Function
def main():
    if "file_uploaded" not in st.session_state:
        st.session_state.file_uploaded = False

    st.set_page_config(layout="wide")
    st.title("🤖 RAG System Sample")
    
    # 줄바꿈 적용
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

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