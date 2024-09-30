#document.py
import os
import sys
import json

##Setters and getters for data retrieval/persistance
class Document:
    def __init__(self, project_name, doc_id, status='UNVISITED'):
        self.project_name = project_name
        self.doc_id = doc_id
        self.status = status

        os.makedirs(os.path.join(self.project_name, 'documents', doc_id), exist_ok=True)

        self.doc_status_filepath = os.path.join(project_name, 'documents', doc_id, 'status.txt')

        if os.path.exists(self.doc_status_filepath):
            self.status = self.load_file(self.doc_status_filepath)
        else:
            self.save_file(self.doc_status_filepath, status, 'txt')
        print(self.status)
            
    def save_file(self, filepath, content, ftype='txt'):
        match ftype:
            case 'json':
                with open(filepath, 'w') as file:
                    json.dump(content, file)

            case 'txt':
                with open(filepath, 'w', encoding='utf-8') as file:
                    file.write(content)

    def load_file(self, filepath, ftype='txt'):
        match ftype:
            case 'json':
                with open(filepath, 'r') as file:
                    d = json.load(file)
                    return d
                
            case 'txt':
                with open(filepath, 'r', encoding='utf-8') as file:
                    d = file.read()
                    return d

    def set_status(self, status):
        self.status = status
        self.save_file(self.doc_status_filepath, status, 'txt')

    def get_source(self):
        source_filepath = os.path.join(self.project_name, 'documents', self.doc_id, 'source.txt')
        if os.path.exists(source_filepath):
            return self.load_file(source_filepath, 'txt')
        else:
            return None

    def set_source(self, value):
        source_filepath = os.path.join(self.project_name, 'documents', self.doc_id, 'source.txt')
        return self.save_file(source_filepath, value, 'txt')

    def get_trimmed(self):
        trimmed_filepath = os.path.join(self.project_name, 'documents', self.doc_id, 'trimmed.txt')
        if os.path.exists(trimmed_filepath):
            return self.load_file(trimmed_filepath) 
        else:
            return None

    def set_trimmed(self, value):
        trimmed_filepath = os.path.join(self.project_name, 'documents', self.doc_id, 'trimmed.txt')
        self.save_file(trimmed_filepath, value) 

    def set_chunks(self, chunks, chunk_type):
        for size in chunks.keys():
            os.makedirs(os.path.join(self.project_name, 'documents', self.doc_id, 'chunks', chunk_type, size), exist_ok=True)
            for i in range(0, len(chunks[size])):
                chunk = chunks[size][i]
                filepath = os.path.join(self.project_name, 'documents', self.doc_id, 'chunks', chunk_type, size, f'{i}.txt')
                self.save_file(filepath, chunk)

    def get_chunks(self, chunk_type):
        chunks = {}
        with os.scandir(os.path.join(self.project_name, 'documents', self.doc_id, 'chunks', chunk_type)) as chunks_folder:
            for directory in chunks_folder:
                if directory.is_dir():
                    chunks[directory.name] = []
                    with os.scandir(os.path.join(self.project_name, 'documents', self.doc_id, 'chunks', chunk_type, directory.name)) as size_folder:
                        for chunk in size_folder:
                            chunk_fp = os.path.join(self.project_name, 'documents', self.doc_id, 'chunks', chunk_type, directory.name, chunk.name)
                            text = self.load_file(chunk_fp)
                            chunks[directory.name].append(text)
        return chunks

    def set_raw_chunks(self, chunks):
        return self.set_chunks(chunks, 'raw')
    def get_raw_chunks(self):
        return self.get_chunks('raw')

    def set_pretty_chunks(self, chunks):
        return self.set_chunks(chunks, 'pretty')
    def get_pretty_chunks(self):
        return self.get_chunks('pretty')

    def save_synthetic_chunks(self, synth_chunks):
        os.makedirs(os.path.join(self.project_name, 'documents', self.doc_id,'chunks', 'synthetic'), exist_ok=True)
        for i in range(0, len(synth_chunks)):
            filepath = os.path.join(self.project_name, 'documents', self.doc_id,'chunks', 'synthetic', f'{i}.json')
            self.save_file(filepath, synth_chunks[i], 'json')

    # def get_vectors(self):
    #     #TODO
    #     print('TODO GET VECS')
