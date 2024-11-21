import threading
import streamlit as st
from src.query.llm_intergration import generate_response
from src.watcher.directory_watcher import DirectoryHandler
from watchdog.observers import Observer
from src.config import DATA_DIR
import time

def run_watcher():
    """
    Watcher를 실행하는 함수 (스레드에서 실행).
    """
    observer = Observer()
    event_handler = DirectoryHandler()
    observer.schedule(event_handler, path=DATA_DIR, recursive=True)
    observer.start()
    st.session_state.observer = observer
    print(f"Watcher started for directory: {DATA_DIR}")
    
    try:
        while True:
            time.sleep(1)
            if not observer.is_alive():
                break
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    print("Watcher thread exiting")

def stop_watcher():
    """
    Watcher를 종료하는 함수.
    """
    if 'observer' in st.session_state and st.session_state.observer is not None:
        st.session_state.observer.stop()
        st.session_state.observer.join()
        st.session_state.observer = None
        print("Watcher stopped.")

def main():
    # Streamlit 세션 상태 초기화
    if "watcher_running" not in st.session_state:
        st.session_state.watcher_running = False
    if 'observer' not in st.session_state:
        st.session_state.observer = None
    if 'watcher_thread' not in st.session_state:
        st.session_state.watcher_thread = None

    # 페이지 제목
    st.title("RAG System Query Interface")

    # Watcher 실행 및 종료 버튼
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Run Watcher", key="run_watcher_button"):
            if not st.session_state.watcher_running:
                st.session_state.watcher_running = True
                st.write("Watcher is running in the background...")
                watcher_thread = threading.Thread(target=run_watcher)
                st.session_state.watcher_thread = watcher_thread
                watcher_thread.start()
                st.success("Watcher has been started.")
            else:
                st.info("Watcher is already running.")

    with col2:
        if st.button("Stop Watcher", key="stop_watcher_button"):
            if st.session_state.watcher_running:
                st.session_state.watcher_running = False
                stop_watcher()
                # 스레드가 종료될 때까지 기다립니다.
                if st.session_state.watcher_thread is not None:
                    st.session_state.watcher_thread.join()
                    st.session_state.watcher_thread = None
                st.success("Watcher has been stopped.")
            else:
                st.info("Watcher is not running.")

    # 워처 상태 표시
    if st.session_state.watcher_running:
        st.markdown("**Watcher Status:** 🟢 Running")
    else:
        st.markdown("**Watcher Status:** 🔴 Stopped")

    # 사용자 질의 입력
    query = st.text_input("Enter your question:", placeholder="Ask a question about your documents...")

    # 검색 결과 수 옵션
    top_k = st.slider("Number of documents to retrieve:", min_value=1, max_value=10, value=5)

    # 결과 생성 버튼
    if st.button("Search"):
        if query.strip():
            st.write("Searching and generating response...")
            response = generate_response(query, top_k=top_k)
            st.subheader("Response:")
            st.write(response)
        else:
            st.warning("Please enter a valid question.")

if __name__ == "__main__":
    main()