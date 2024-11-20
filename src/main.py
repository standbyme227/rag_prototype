from src.config import DATA_DIR
from src.watcher.directory_watcher import start_watching
from src.query.llm_integration import generate_response

if __name__ == "__main__":
    # Start directory watcher
    print("Starting directory watcher...")
    start_watching(DATA_DIR)

    # Test query
    query = "What is the main topic of the documents?"
    response = generate_response(query)
    print("Response:", response)