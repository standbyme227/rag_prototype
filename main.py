import multiprocessing
import streamlit as st
from src.query.llm_intergration import generate_response
from src.watcher.directory_watcher import DirectoryHandler
from watchdog.observers import Observer
from src.config import DATA_DIR
import time

def run_watcher(stop_event):
    """
    워처를 실행하는 함수 (프로세스에서 실행).
    """
    observer = Observer()
    event_handler = DirectoryHandler()
    observer.schedule(event_handler, path=DATA_DIR, recursive=True)
    observer.start()
    print(f"Watcher started for directory: {DATA_DIR}")
    
    try:
        while not stop_event.is_set():
            time.sleep(0.1)
    except Exception as e:
        print(f"Watcher encountered an error: {e}")
    finally:
        observer.stop()
        observer.join()
        print("Watcher process exiting")

def main():
    # Streamlit 세션 상태 초기화
    if "watcher_running" not in st.session_state:
        st.session_state.watcher_running = False
    if 'stop_event' not in st.session_state:
        st.session_state.stop_event = None
    if 'watcher_process' not in st.session_state:
        st.session_state.watcher_process = None

    # 페이지 제목
    st.title("RAG System Query Interface")

    # Watcher 실행 및 종료 버튼
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Run Watcher", key="run_watcher_button"):
            if not st.session_state.watcher_running:
                st.session_state.watcher_running = True
                st.write("Watcher is running in the background...")
                stop_event = multiprocessing.Event()
                st.session_state.stop_event = stop_event
                watcher_process = multiprocessing.Process(target=run_watcher, args=(stop_event,))
                st.session_state.watcher_process = watcher_process
                watcher_process.start()
                st.success("Watcher has been started.")
            else:
                st.info("Watcher is already running.")

    with col2:
        if st.button("Stop Watcher", key="stop_watcher_button"):
            if st.session_state.watcher_running:
                st.session_state.watcher_running = False
                st.session_state.stop_event.set()
                if st.session_state.watcher_process is not None:
                    st.session_state.watcher_process.join()
                    st.session_state.watcher_process = None
                st.success("Watcher has been stopped.")
            else:
                st.info("Watcher is not running.")

    # 워처 상태 표시
    if st.session_state.watcher_running:
        st.markdown("**Watcher Status:** 🟢 Running")
    else:
        st.markdown("**Watcher Status:** 🔴 Stopped")

    # 사용자 질의 입력
    query = st.text_area("Enter your question:", placeholder="Ask a question about your documents...")

    # 검색 결과 수 옵션
    top_k = st.slider("Number of documents to retrieve:", min_value=1, max_value=10, value=5)

    # 결과 생성 버튼
# 결과 생성 버튼
    if st.button("Search"):
        if query.strip():
            # 상태 메시지 출력 영역 생성
            status_placeholder = st.empty()
            status_placeholder.write("**Searching and generating response...**")
            
            # 검색 결과 생성
            response = generate_response(query, top_k=top_k)
            
            # 상태 메시지 삭제
            status_placeholder.empty()
            
            # 검색 결과 출력
            st.subheader("🤖 답변 :")
            st.markdown(response)
        else:
            st.warning("Please enter a valid question.")

if __name__ == "__main__":
    main()