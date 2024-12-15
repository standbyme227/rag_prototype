# file_manager.py

import json
import os
from typing import List, Dict, Optional
import streamlit as st
from src.config import DATA_DIR, VECTORSTORE_VERSION
from src.embedding.vectorstore_handler import remove_from_vectorstore, VectorStoreManager

class FileManager:
    def __init__(self, file_list_path: str):
        self.file_list_path = file_list_path
        
    def _set_file_metadata(self, metadata: Dict) -> Dict:
        """메타데이터에서 필요한 정보만 추출"""
        return {
            "doc_id": metadata.get('doc_id', ""),
            "filename": metadata.get('file_name', "Unknown")
        }

    def _get_unique_metadatas(self) -> tuple:
        """벡터스토어에서 고유한 메타데이터 추출"""
        vectorstore = VectorStoreManager.get_instance()
        all_metadatas = vectorstore.get()['metadatas']
        
        unique_metadatas = []
        unique_doc_ids = []
        
        for metadata in all_metadatas:
            doc_id = metadata.get('doc_id')
            if doc_id not in unique_doc_ids:
                unique_metadatas.append(metadata)
                unique_doc_ids.append(doc_id)
                
        return unique_metadatas, unique_doc_ids

    def create_file_list(self) -> List[Dict]:
        """새로운 파일 목록 생성"""
        unique_metadatas, _ = self._get_unique_metadatas()
        return [self._set_file_metadata(metadata) for metadata in unique_metadatas]

    def load_file_list(self) -> List[Dict]:
        """파일 목록 로드 및 동기화"""
        if not os.path.exists(self.file_list_path):
            file_list = self.create_file_list()
            self.save_file_list(file_list)
            return file_list

        with open(self.file_list_path, 'r', encoding='utf-8') as f:
            file_list = json.load(f)
            
        if not isinstance(file_list, list):
            raise ValueError("file_list.json should contain a list of file entries.")
            
        # VectorDB와 동기화
        _, unique_doc_ids = self._get_unique_metadatas()
        file_list = self._sync_with_vectorstore(file_list, unique_doc_ids)
        
        # 중복 제거
        return self._remove_duplicates(file_list)

    def _sync_with_vectorstore(self, file_list: List[Dict], unique_doc_ids: List[str]) -> List[Dict]:
        """VectorDB와 파일 목록 동기화"""
        # 벡터스토어에 없는 항목 제거
        file_list = [f for f in file_list if f.get("doc_id") in unique_doc_ids]
        
        # 새로운 항목 추가
        exist_doc_ids = [f.get("doc_id") for f in file_list]
        unique_metadatas, _ = self._get_unique_metadatas()
        
        for doc_id in unique_doc_ids:
            if doc_id not in exist_doc_ids:
                for metadata in unique_metadatas:
                    if metadata.get('doc_id') == doc_id:
                        file_list.append(self._set_file_metadata(metadata))
                        break
                        
        return file_list

    def _remove_duplicates(self, file_list: List[Dict]) -> List[Dict]:
        """중복 doc_id 제거"""
        seen_doc_ids = set()
        unique_file_list = []
        
        for file_data in file_list:
            doc_id = file_data.get("doc_id")
            if doc_id not in seen_doc_ids:
                seen_doc_ids.add(doc_id)
                unique_file_list.append(file_data)
                
        return unique_file_list

    def save_file_list(self, file_list: List[Dict]) -> None:
        """파일 목록 저장"""
        with open(self.file_list_path, 'w', encoding='utf-8') as f:
            json.dump(file_list, f, ensure_ascii=False, indent=4)

    def remove_file(self, file_id: str) -> None:
        """파일 삭제"""
        file_list = self.load_file_list()
        file_to_remove = next((f for f in file_list if f.get("doc_id") == file_id), None)

        if file_to_remove:
            doc_id = file_to_remove.get("doc_id")
            if doc_id:
                remove_from_vectorstore(doc_id=file_to_remove.get("doc_id"), remove_all_versions=True)
            
            file_list = [f for f in file_list if f.get("doc_id") != file_id]
            self.save_file_list(file_list)
            st.success("파일이 삭제되었습니다.")
        else:
            st.warning("해당 파일을 찾을 수 없습니다.")

    def add_file(self, metadatas: List[Dict]) -> None:
        """새 파일 추가"""
        file_list = self.load_file_list()
        existing_doc_ids = {f.get("doc_id") for f in file_list}
        
        new_files = []
        for metadata in metadatas:
            file_data = self._set_file_metadata(metadata)
            if file_data.get("doc_id") not in existing_doc_ids:
                new_files.append(file_data)
                
        if new_files:
            file_list.extend(new_files)
            self.save_file_list(file_list)