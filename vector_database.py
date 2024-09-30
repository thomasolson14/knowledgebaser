#vector-database.py
from llm_api import llmAPI
import hashlib

#Use vectors to map metadata to filepath
class VectorDB:
    def __init__(self, project_name):
        self.project_name = project_name
        self.llm_api = llmAPI()
        self.topic_db = DB()
        self.question_db = DB()
        self.keyword_db = DB()

    def load(self):
        self.topic_db.load_from_json(os.path.join(self.project_name, 'index/topics.json'))
        self.topic_db.build_index()
        self.question_db.load_from_json(os.path.join(self.project_name, 'index/questions.json'))
        self.question_db.build_index()
        self.keyword_db.load_from_json(os.path.join(self.project_name, 'index/keywords.json'))
        self.keyword_db.build_index()

    def save(self):
        os.makedirs(os.path.join(self.project_name, 'index'), exist_ok=True)
        self.topic_db.save_to_json(os.path.join(self.project_name, 'index/topics.json'))
        self.question_db.save_to_json(os.path.join(self.project_name, 'index/questions.json'))
        self.keyword_db.save_to_json(os.path.join(self.project_name, 'index/keywords.json'))

    def index(self, to_index):
        topic_vectors = []
        if 'topics' in to_index:
            topic_vectors = to_index['topics']
        if len(topic_vectors) > 0:
            for v in topic_vectors:
                #emb = self.llm_api.get_embedding(v['topic'])
                self.topic_db.add_vector(self.id_from_str(v['filepath']), v['filepath'], v['topic'])
            
            self.topic_db.build_index(n_neighbors=3, metric='cosine')

        keyword_vectors = []
        if 'keywords' in to_index:
            keyword_vectors = to_index['keywords']
        if len(keyword_vectors) > 0:
            for v in keyword_vectors:
                #emb = self.llm_api.get_embedding(v['keyword'])
                
                self.keyword_db.add_vector(self.id_from_str(v['filepath']), v['filepath'], v['keyword'])
            self.keyword_db.build_index(n_neighbors=8, metric='cosine')

        question_vectors = []
        if 'questions' in to_index:
            question_vectors = to_index['questions']
        if len(keyword_vectors) > 0:
            for v in question_vectors:
                #emb = self.llm_api.get_embedding(v['keyword'])
                self.question_db.add_vector(self.id_from_str(v['filepath']), v['filepath'], v['question'])
            self.question_db.build_index(n_neighbors=3, metric='cosine')


    def search(self, search_type, query, k):
        match search_type:
            case 'topics':
                db = self.topic_db
            case 'keywords':
                db = self.keyword_db
            case 'questions':
                db = self.question_db
        return db.query_kNN(query, k)



    def id_from_str(self, text):
        sha256 = hashlib.sha256()
        sha256.update(text.encode('utf-8'))
        hash_hex = sha256.hexdigest()
        return hash_hex.lower()   



##
from sentence_transformers import SentenceTransformer
from sklearn.neighbors import NearestNeighbors
import numpy as np
import os
import json

class DB:
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)
        self.ids = []
        self.file_paths = []
        self.vectors = []
        self.index = None

    def add_vector(self, id, file_path, text):
        print(f"ADDING VECTOR: {file_path}")
        embedding = self.model.encode(text)
        self.ids.append(id)
        self.file_paths.append(file_path)
        self.vectors.append(embedding)

    def build_index(self, n_neighbors=5, metric='cosine'):
        print("Building index...")
        try:
            if self.vectors is None:
                raise ValueError("No vectors to index. Add vectors before building the index.")
            
            # Convert the list of vectors to a 2D NumPy array
            self.vectors_array = np.array(self.vectors)
            
            # Validate the shape of vectors_array
            if len(self.vectors_array.shape) != 2 or (len(self.vectors_array.shape) > 0 and self.vectors_array.shape[1] == 0):
                raise ValueError("Each vector should have at least one feature.")
            
            # Initialize and fit the NearestNeighbors model
            self.index = NearestNeighbors(n_neighbors=n_neighbors, metric=metric)
            self.index.fit(self.vectors_array)
            
            print("Index built successfully.")
        except:
            print("build index failed")


    def query_kNN(self, text, k=5):
        if self.index is None:
            raise ValueError("Index not built. Call build_index() after adding vectors.")
        
        query_vec = self.model.encode(text).reshape(1, -1)
        distances, indices = self.index.kneighbors(query_vec, n_neighbors=k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            result = {
                'id': self.ids[idx],
                'file_path': self.file_paths[idx],
                'distance': dist
            }
            results.append(result)
        return results

    def save_to_json(self, file_path):
        data = {
            'ids': self.ids,
            'file_paths': self.file_paths,
            'vectors': [vec.tolist() for vec in self.vectors]  # Convert numpy arrays to lists
        }
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        print(f"Vector database saved to {file_path}.")

    def load_from_json(self, file_path):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"No such file: '{file_path}'")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.ids = data.get('ids', [])
        self.file_paths = data.get('file_paths', [])
        self.vectors = [np.array(vec) for vec in data.get('vectors', [])]
        self.index = None  # Invalidate the current index
        print(f"Vector database loaded from {file_path}.")
