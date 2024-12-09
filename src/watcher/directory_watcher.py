import os
import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from src.preprocessing.preprocessor import preprocess_documents
from src.embedding.vectorstore_handler import save_to_vectorstore, remove_from_vectorstore, exists_in_vectorstore
from src.config import DATA_DIR
from src.loader.loader import load_documents  # loader.py의 load_documents 함수

# 로거 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def ignore_ignored_files(func):
    def wrapper(self, event, *args, **kwargs):
        if self.is_ignore_file(event.src_path):
            logging.info(f"Ignored file: {event.src_path}")
            return
        return func(self, event, *args, **kwargs)
    return wrapper

class DirectoryHandler(FileSystemEventHandler):
    """
    파일 생성, 수정, 삭제 이벤트를 처리하는 핸들러.
    """
    ignored_extensions = (".ds_store",)

    def __init__(self, batch_processing_interval=1):
        super().__init__()
        self.modified_files = set()
        self.deleted_files = set()
        self.batch_processing_interval = batch_processing_interval  # 배치 처리 간격 (초)
        self.last_processed_time = time.time()
        
    @ignore_ignored_files
    def on_created(self, event):
        if event.is_directory:
            logging.info(f"Directory created: {event.src_path}")
            self.handle_directory(event.src_path)
        else:
            logging.info(f"File created: {event.src_path}")
            self.modified_files.add(event.src_path)
        self.try_batch_process()  # 이벤트 발생 시 배치 처리 시도

    @ignore_ignored_files
    def on_modified(self, event):
        if event.is_directory:
            return
        logging.info(f"File modified: {event.src_path}")
        self.modified_files.add(event.src_path)
        self.try_batch_process()  # 이벤트 발생 시 배치 처리 시도

    @ignore_ignored_files
    def on_deleted(self, event):
        if event.is_directory:
            return
        logging.info(f"File deleted: {event.src_path}")
        self.deleted_files.add(event.src_path)
        self.try_batch_process()  # 이벤트 발생 시 배치 처리 시도

    def handle_directory(self, dir_path):
        """
        디렉토리가 생성되었을 때 해당 디렉토리 내의 모든 파일을 처리.
        """
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                self.modified_files.add(file_path)
        self.try_batch_process()  # 디렉토리 생성 시 배치 처리 시도

    def try_batch_process(self):
        """
        배치 처리를 배치 처리 간격에 따라 조건부로 수행.
        """
        current_time = time.time()
        if current_time - self.last_processed_time >= self.batch_processing_interval:
            logging.info("try_batch_process() called, interval reached")
            self.batch_process()
            self.last_processed_time = current_time
        else:
            logging.info("try_batch_process() called, but interval not reached yet")

    def batch_process(self):
        """
        누적된 파일들을 한꺼번에 처리.
        """
        if self.modified_files:
            logging.info("Processing modified/created files...")
            file_paths = list(self.modified_files)
            try:
                self.handle_event(file_paths)
                self.modified_files.clear()
            except Exception as e:
                logging.error(f"Error processing files {file_paths}: {e}", exc_info=True)

        if self.deleted_files:
            logging.info("Processing deleted files...")
            file_paths = list(self.deleted_files)
            try:
                self.handle_deletion(file_paths)
                self.deleted_files.clear()
            except Exception as e:
                logging.error(f"Error removing files {file_paths} from vectorstore: {e}", exc_info=True)

    def handle_event(self, file_paths):
        # 전처리 전에는 중복 체크하지 않음
        new_files = file_paths

        if not new_files:
            logging.info("No new files to process.")
            return

        processed_docs = []
        for fp in new_files:
            try:
                docs = load_documents([fp])
                processed = preprocess_documents(docs)  
                # preprocess_documents 내에서 doc_id, content_hash를 메타데이터에 포함한다고 가정
                processed_docs.extend(processed)
            except Exception as e:
                logging.error(f"Error processing file {fp}: {e}", exc_info=True)

        # 벡터스토어에 저장하기 전에 중복 체크
        # 예: exists_in_vectorstore를 doc_id, content_hash 기반으로 변경했을 경우
        final_docs_to_save = []
        for doc in processed_docs:
            doc_id = doc.metadata.get("doc_id")
            content_hash = doc.metadata.get("content_hash")
            if doc_id and content_hash:
                if not exists_in_vectorstore(doc_id, content_hash):
                    final_docs_to_save.append(doc)
                else:
                    logging.info(f"Document with doc_id={doc_id}, content_hash={content_hash} already exists. Skipping.")
            else:
                # 메타데이터가 불완전하면 일단 저장 시도 (혹은 스킵)
                final_docs_to_save.append(doc)

        if final_docs_to_save:
            try:
                contents = [d.page_content for d in final_docs_to_save]
                metadatas = [d.metadata for d in final_docs_to_save]
                save_to_vectorstore(contents, metadatas)
                logging.info(f"Files processed and saved to vectorstore: {[d.metadata.get('path') for d in final_docs_to_save]}")
            except Exception as e:
                logging.error(f"Error saving to vectorstore: {e}", exc_info=True)
        else:
            logging.info("No new documents to save to vectorstore after checking duplicates.")

    def handle_deletion(self, file_paths):
        """
        파일 삭제 이벤트를 처리.
        개별 파일 단위 예외 처리.
        """
        for fp in file_paths:
            try:
                remove_from_vectorstore(fp)
                logging.info(f"File removed from vectorstore: {fp}")
            except Exception as e:
                logging.error(f"Error removing file {fp} from vectorstore: {e}", exc_info=True)
            
    def is_ignore_file(self, file_path):
        """
        Checks if the file should be ignored based on its extension.
        """
        return file_path.lower().endswith(self.ignored_extensions)

def start_watching(directory=DATA_DIR, batch_processing_interval=5):
    """
    디렉토리를 감시하며 파일 이벤트를 처리.
    """
    event_handler = DirectoryHandler(batch_processing_interval=batch_processing_interval)
    observer = Observer()
    observer.schedule(event_handler, path=directory, recursive=True)
    observer.start()
    logging.info(f"Watching directory: {directory}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()