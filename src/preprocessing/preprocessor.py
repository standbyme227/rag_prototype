from src.preprocessing.splitter import split_text
from src.preprocessing.metadata_manager import generate_metadata, manage_versions

def preprocess_documents(documents, chunk_size=1000, chunk_overlap=200):
    """
    문서 전처리: 메타데이터 구성, 청킹, 버전 관리.

    Args:
        documents (list[Document]): 로드된 문서 리스트.
        chunk_size (int): 청킹 크기.
        chunk_overlap (int): 청킹 겹침.

    Returns:
        list[Document]: 전처리된 문서 리스트.
    """
    processed_docs = []
    existing_documents = []  # 기존 문서 리스트 (DB에서 로드된다고 가정)

    # 전처리 시작
    count = 0
    total_count = len(documents)
    print(f"#2 Preprocessing documents, total: {total_count}cnt")
    for doc in documents[:1]:
        count += 1
        # 메타데이터 생성
        # 만약에 'path' 키가 없다면, 파일 경로를 사용한다.
        if 'path' not in doc.metadata:
            doc.metadata['path'] = doc.metadata['source']
        
        print(f"Processing document [{count}]: {doc.metadata['path']}")
        print(doc.page_content)
        metadata = generate_metadata(doc.metadata['path'], doc.page_content)
        doc.metadata.update(metadata)

        # 문서 청킹
        print(f"Splitting document [{count}]: {doc.metadata['path']}")
        if len(doc.page_content) > chunk_size:
            chunked_docs = split_text(doc, chunk_size, chunk_overlap)
            for chunked_doc in chunked_docs:
                metadata = generate_metadata(doc.metadata['path'], chunked_doc.page_content)
                chunked_doc.metadata.update(metadata)
                processed_docs.append(chunked_doc)
        else:
            processed_docs.append(doc)
        
    print(f"Preprocessing done: {count}/{total_count}")
        

    # 버전 관리
    final_documents = []
    print("#3 Managing versions, total: {total_count}cnt")
    v_count = 0
    for new_doc in processed_docs:
        v_count += 1
        final_documents = manage_versions(existing_documents, new_doc)
        print(f"Managing version [{v_count}]: {new_doc.metadata['path']}")

    return final_documents