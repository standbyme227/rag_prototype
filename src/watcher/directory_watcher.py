# src/watcher/directory_watcher.py

import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from src.preprocessing.preprocessor import preprocess_documents
from src.embedding.vectorstore_handler import save_to_vectorstore, remove_from_vectorstore
from src.config import DATA_DIR
from src.loader.loader import load_documents  # loader.py의 load_documents 함수


def ignore_ignored_files(func):
    def wrapper(self, event, *args, **kwargs):
        if event.is_directory:
            # Optional: Handle directories if needed
            return
        if self.is_ignore_file(event.src_path):
            print(f"Ignored file: {event.src_path}")
            return
        return func(self, event, *args, **kwargs)
    return wrapper

class DirectoryHandler(FileSystemEventHandler):
    """
    파일 생성, 수정, 삭제 이벤트를 처리하는 핸들러.
    """
    def __init__(self):
        super().__init__()
        self.modified_files = set()
        self.deleted_files = set()
        self.batch_processing_interval = 2  # 배치 처리 간격 (초)
        self.last_processed_time = time.time()
        
    ignored_extensions = (".ds_store",)
        
    @ignore_ignored_files
    def on_created(self, event):
        if event.is_directory:
            print(f"Directory created: {event.src_path}")
            self.handle_directory(event.src_path)
        else:
            print(f"File created: {event.src_path}")
            self.modified_files.add(event.src_path)
            self.try_batch_process()

    @ignore_ignored_files
    def on_modified(self, event):
        if event.is_directory:
            return
        print(f"File modified: {event.src_path}")
        self.modified_files.add(event.src_path)
        self.try_batch_process()

    @ignore_ignored_files
    def on_deleted(self, event):
        if event.is_directory:
            return
        print(f"File deleted: {event.src_path}")
        self.deleted_files.add(event.src_path)
        self.try_batch_process()

    def handle_directory(self, dir_path):
        """
        디렉토리가 생성되었을 때 해당 디렉토리 내의 모든 파일을 처리.
        """
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                self.modified_files.add(file_path)
        self.try_batch_process()

    def try_batch_process(self):
        """
        배치 처리를 일정 간격으로 수행.
        """
        current_time = time.time()
        if current_time - self.last_processed_time >= self.batch_processing_interval:
            self.batch_process()
            self.last_processed_time = current_time

    def batch_process(self):
        """
        누적된 파일들을 한꺼번에 처리.
        """
        if self.modified_files:
            print("Processing modified/created files...")
            file_paths = list(self.modified_files)
            self.modified_files.clear()
            self.handle_event(file_paths)
        if self.deleted_files:
            print("Processing deleted files...")
            file_paths = list(self.deleted_files)
            self.deleted_files.clear()
            self.handle_deletion(file_paths)

    def handle_event(self, file_paths):
        """
        파일 생성 및 수정 이벤트를 처리.
        """
        try:
            # 1. 문서 로드 및 전처리
            documents = load_documents(file_paths)
            processed_docs = preprocess_documents(documents)

            # 2. 벡터스토어에 저장
            # contents = [doc.page_content for doc in processed_docs]
            # metadatas = [doc.metadata for doc in processed_docs]
            # print(contents, metadatas)
            # save_to_vectorstore(contents, metadatas)
            print(f"Files processed and saved to vectorstore: {file_paths}")

        except Exception as e:
            print(f"Error processing files {file_paths}: {e}")

    def handle_deletion(self, file_paths):
        """
        파일 삭제 이벤트를 처리.
        """
        try:
            for file_path in file_paths:
                remove_from_vectorstore(file_path)
            print(f"Files removed from vectorstore: {file_paths}")

        except Exception as e:
            print(f"Error removing files {file_paths} from vectorstore: {e}")
            
    
    def is_ignore_file(self, file_path):
        """
        Checks if the file should be ignored based on its extension.
        """
        return file_path.lower().endswith(self.ignored_extensions)

def start_watching(directory=DATA_DIR):
    """
    디렉토리를 감시하며 파일 이벤트를 처리.
    """
    event_handler = DirectoryHandler()
    observer = Observer()
    observer.schedule(event_handler, path=directory, recursive=True)
    observer.start()
    print(f"Watching directory: {directory}")
    try:
        while True:
            time.sleep(1)
            event_handler.try_batch_process()  # 메인 루프에서도 배치 처리 시도
    except KeyboardInterrupt:
        observer.stop()
    observer.join()