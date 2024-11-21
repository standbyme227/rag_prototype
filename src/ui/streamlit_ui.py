import sys
import os
import streamlit as st
from src.query import generate_response  # 응답 생성 함수 import
from src.watcher.directory_watcher import start_watcher  # Watcher 실행 함수 import

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

def main():
    # 페이지 제목
    st.title("RAG System Query Interface")

    # Watcher 실행 버튼 
    if st.button("Run Watcher"):
        st.write("Watcher is running...")
        try:
            start_watcher()  # Watcher 실행
        except Exception as e:
            st.error(f"An error occurred while running the watcher: {e}")

    # 사용자 질의 입력
    query = st.text_input("Enter your question:", placeholder="Ask a question about your documents...")

    # 검색 결과 수 옵션 (기본값: 5)
    top_k = st.slider("Number of documents to retrieve:", min_value=1, max_value=10, value=5)

    # 결과 생성 버튼
    if st.button("Search"):
        if query.strip():
            st.write("Searching and generating response...")

            # LLM 응답 생성
            response = generate_response(query, top_k=top_k)

            # 결과 출력
            st.subheader("Response:")
            st.write(response)
        else:
            st.warning("Please enter a valid question.")

if __name__ == "__main__":
    main()