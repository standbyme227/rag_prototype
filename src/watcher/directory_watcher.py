import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from src.preprocessing.text_preprocessor import preprocess_file

class DirectoryHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        print(f"File created: {event.src_path}")
        preprocess_file(event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        print(f"File modified: {event.src_path}")
        preprocess_file(event.src_path)

    def on_deleted(self, event):
        print(f"File deleted: {event.src_path}")
        # Handle deletion in vectorstore

def start_watching(directory):
    event_handler = DirectoryHandler()
    observer = Observer()
    observer.schedule(event_handler, path=directory, recursive=True)
    observer.start()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        observer.stop()
    observer.join()