import json
import os
import uuid
import streamlit as st
from src.query.llm_intergration import generate_response
from src.config import DATA_DIR, VECTORSTORE_DIR
from src.embedding.vectorstore_handler import remove_from_vectorstore
from src.preprocessing.metadata_manager import generate_doc_id

# file_list.json 경로
FILE_LIST_PATH = os.path.join(DATA_DIR, "file_list.json")

def load_file_list():
    if os.path.exists(FILE_LIST_PATH):
        with open(FILE_LIST_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_file_list(file_list):
    with open(FILE_LIST_PATH, 'w', encoding='utf-8') as f:
        json.dump(file_list, f, ensure_ascii=False, indent=4)

def remove_file_entry(file_id):
    file_list = load_file_list()
    file_to_remove = None
    
    for f in file_list:
        if f.get("id") == file_id:
            file_to_remove = f
            break
    
    if file_to_remove:
        # doc_id 추출
        doc_id = file_to_remove.get("doc_id")
        if doc_id:
            # vectorDB에서 삭제 로직 호출
            remove_from_vectorstore(file_path=file_to_remove.get("filepath"), remove_all_versions=True)
        
        # 리스트에서 제거
        file_list = [f for f in file_list if f.get("id") != file_id]
        save_file_list(file_list)
        st.success("파일이 삭제되었습니다.")
    else:
        st.warning("해당 파일을 찾을 수 없습니다.")

def add_uploaded_file_to_list(file):
    # 업로드된 파일 처리 로직 (여기서는 단순히 file_list.json에 추가하는 형태)
    # 실제 처리로직(Chunking, 벡터DB 추가 등)은 별도로 구현 필요
    file_list = load_file_list()
    file_path = os.path.join(DATA_DIR, file.name)
    
    # 파일 저장
    with open(file_path, "wb") as f:
        f.write(file.read())
    
    # doc_id 생성 (실제 vectorstore에 추가하는 로직이 있다면, 그 후 doc_id를 할당)
    doc_id = generate_doc_id(file_path)
    file_entry = {
        "id": str(uuid.uuid4()),
        "filename": file.name,
        "filepath": file_path,
        "doc_id": doc_id,
        "metadata": {}  # 필요하면 메타데이터 추가
    }
    file_list.append(file_entry)
    save_file_list(file_list)
    st.success(f"파일 {file.name} 이(가) 업로드되고 목록에 추가되었습니다.")

def main():
    st.set_page_config(layout="wide")
    # 상단 공통 영역: file_list 표시, 검색, 새로고침 버튼
    st.title("RAG System Interface")

    # 검색 기능
    search_col1, search_col2 = st.columns([3,1])
    with search_col1:
        search_query = st.text_input("Search in file list:", "")
    with search_col2:
        if st.button("Refresh"):
            # file_list.json 다시 로드 -> 아무것도 안해도 load_file_list 호출시 최신화
            st.experimental_rerun()

    file_list = load_file_list()
    # 검색 기능 적용
    if search_query.strip():
        filtered_files = [f for f in file_list if search_query.lower() in f.get("filename", "").lower()]
    else:
        filtered_files = file_list

    st.subheader("Stored Documents")
    if not filtered_files:
        st.info("No files found.")
    else:
        # 파일 리스트 표시: hover 시 삭제버튼 표시
        for f in filtered_files:
            filename = f.get("filename", "No Name")
            file_id = f.get("id")
            
            # Streamlit에서는 hover 시 버튼 표시하는 기능이 직접적으로는 없음.
            # 대신 expand나 container를 사용하거나, 세션 상태로 구현할 수 있음.
            # 여기서는 간단히 파일명 옆에 삭제 버튼을 항상 표시하는 것으로 대체.
            # (hover 기능은 pure Streamlit 기본 기능으로는 구현 어렵고, st_tooltips나 HTML/CSS 커스텀 필요.)
            
            file_col1, file_col2 = st.columns([9,1])
            with file_col1:
                st.write(filename)
            with file_col2:
                if st.button("❌", key=file_id):
                    if st.confirm(f"정말로 {filename}을(를) 삭제하시겠습니까?"):
                        remove_file_entry(file_id)
                        st.experimental_rerun()

    # 탭 구성
    tab1, tab2 = st.tabs(["Home", "Search"])

    with tab1:
        st.header("Home")
        st.write("데이터 업로드 영역")

        # Drag and Drop + 로컬 파일 선택
        # Streamlit은 기본적으로 drag and drop 기능을 제공하는 st.file_uploader 사용
        uploaded_files = st.file_uploader("Upload files", accept_multiple_files=True)
        if uploaded_files:
            for uploaded_file in uploaded_files:
                add_uploaded_file_to_list(uploaded_file)
            st.experimental_rerun()
        
        # 필요시 추가 로직 구현 (예: watcher 로직 주석처리)
        # st.write("Watcher 관련 코드는 주석 처리되었습니다.")

    with tab2:
        st.header("Search")
        st.write("문서 기반 Q&A 인터페이스")

        # 대화 형식으로 검색 결과를 제공하기 위해 이전 대화 기록 관리 필요
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []

        # 사용자 질의 입력
        query = st.text_area("Enter your question:", placeholder="Ask about your documents...")

        # 검색 결과 수 옵션
        top_k = st.slider("Number of documents to retrieve:", min_value=1, max_value=20, value=10)

        if st.button("Send"):
            if query.strip():
                # 사용자 메시지 기록
                st.session_state.chat_history.append(("user", query))
                
                # 검색 및 응답 생성
                response = generate_response(query, top_k=top_k, is_test_version=True)
                
                # 봇의 응답 기록
                st.session_state.chat_history.append(("bot", response))
                st.experimental_rerun()
            else:
                st.warning("Please enter a valid question.")

        # 대화 내역 표시 (스크롤 가능 영역)
        st.subheader("Conversation")
        chat_container = st.container()
        with chat_container:
            for role, message in st.session_state.chat_history:
                if role == "user":
                    st.markdown(f"**You:** {message}")
                else:
                    st.markdown(f"**Bot:** {message}")

        # 대화창을 스크롤 가능하게 하려면, streamlit에서는 기본적으로 스크롤바가 지원되지만
        # 긴 대화 시 자연히 스크롤이 생깁니다.
        # 별도 스타일이나 st.chat_message 사용도 가능 (Streamlit 최신버전에서는 st.chat_message 이용)

if __name__ == "__main__":
    main()