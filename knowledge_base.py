#knowledge_base.py
import os
import sys
import json
import hashlib

from crawler import Crawler
from refiner import Refiner
from vector_database import VectorDB
from document import Document

from llm_api import llmAPI

class KnowledgeBase:
    def __init__(self, project_settings):
        self.project_name = project_settings['project_name']
        self.base_url = project_settings['base_url']
        self.project_settings = project_settings
        self.to_visit = []
        self.to_process = []
        self.crawler = Crawler(self.project_name, self.base_url)
        self.refiner = Refiner(self.project_name)
        self.index = VectorDB(self.project_name)
        self.llm_api = llmAPI()

    #Build - Save project settings, save_file, begin update()
    def build(self):
        os.makedirs(self.project_name, exist_ok=True)
        self.to_visit = [self.base_url]

        project_settings_filepath = os.path.join(self.project_name, 'project_settings.json')
        with open(project_settings_filepath, 'w') as file:
            json.dump(self.project_settings, file)
        save_file_filepath = os.path.join(self.project_name, 'save.json')


        self.save()
        self.update()

    #save crawl queue and chunk/process queue incase process is interupted
    def save(self):
        print("Saving")
        try:
            save_file_filepath = os.path.join(self.project_name, 'save.json')
            save_file = {'to_visit': self.to_visit, 'to_process': self.to_process}
            with open(save_file_filepath, 'w') as file:
                json.dump(save_file, file)

            self.index.save()
        except Exception as e:
            print(e)
            print("Save failed.")

    #load crawl queue and chunk/process queue
    def load(self):
        print("Load Saved Data.")
        try:
            save_file_filepath = os.path.join(self.project_name, 'save.json')

            if os.path.exists(save_file_filepath):
                with open(save_file_filepath, 'r') as file:
                    save_file = json.load(file)
                    print(save_file)
                if 'to_visit' in save_file:
                    self.to_visit = save_file['to_visit']
                if 'to_process' in save_file:
                    self.to_process = save_file['to_process']

            print(self.to_visit)
            self.index.load()

        except Exception as e:
            print(e)
            print("Load Failed.")

    #Update - Crawl any new pages, process downloaded pages into chunks + search metadata, update vectorDB
    def update(self):
        try:
            #Visit New Pages
            print("Explore")
            while len(self.to_visit) > 0:
                url = self.to_visit.pop()
                print(url)
                try:
                    doc_id, new_links = self.crawler.crawl(url)
                    if doc_id is not None:
                        self.to_process.append(doc_id)
                    if len(new_links) > 0:
                        self.to_visit = self.to_visit + new_links
                        self.save()
                except Exception as e:
                    print(e)
            print("Explore Complete")
            
            print("Process Documents")
            while len(self.to_process) > 0:
                print(f"Count remaining to_process: {len(self.to_process)}")
                doc_id = self.to_process.pop()
                print(doc_id)
                try:
                    to_index = self.refiner.process(doc_id)
                    if to_index:
                        print("start indexing")
                        self.index.index(to_index)

                except Exception as e:
                    print("Exception:")
                    print(e)
                self.save()

            print()

        except Exception as e:
            print(e)
            self.save()

        #ends with save
        self.save()

    #Add all discovered documents to the queue
    def process_all_documents(self):
        self.to_process = []
        with os.scandir(os.path.join(self.project_name, 'documents')) as documents:
            for entry in documents:
                if entry.is_dir():
                    print(entry.name)
                    doc = Document(self.project_name, entry.name)
                    if doc.status == 'DOWNLOADED':
                        self.to_process.append(doc.doc_id)
                    if doc.status == 'TRIMMED':
                        self.to_process.append(doc.doc_id)
                    if doc.status == 'CHUNKED':
                        self.to_process.append(doc.doc_id)
                    print(f"DocStatus - {doc.status}")
        print(f"to_process: {self.to_process}")
        self.save()
        self.update()
    #Search (kNN) 
    def search(self, query, t_k=3, q_k=5, k_k=10):
        topic_vectors = self.index.search('topics', query, 1)
        topic_vectors.sort(reverse=True, key=lambda x: x['distance'])

        question_vectors = self.index.search('questions', query, q_k)
        question_vectors.sort(reverse=True, key=lambda x: x['distance'])

        keyword_vectors = self.index.search('keywords', query, k_k)
        keyword_vectors.sort(reverse=True, key=lambda x: x['distance'])

        return {'topics': topic_vectors, 'questions': question_vectors, 'keywords': keyword_vectors}

    #Answer - RAG based off search results
    def answer(self, query):
        print(f"Answer: {query}")
        results = self.search(query)
        for topic in results['topics']:
            tfp = os.path.join(self.project_name, 'documents', topic['file_path'])
            with open(tfp, 'r', encoding='utf-8') as file:
                t_text = file.read()
            for question in results['questions']:
                qfp = os.path.join(self.project_name, 'documents', question['file_path'])
                with open(qfp, 'r', encoding='utf-8') as file:
                    q_text = file.read()
                answer = self.llm_api.answer_query(query, t_text, q_text)
                if answer:
                    print("AND THE ANSWER IS!")
                    return answer
        print("No Exact answers, check keyword results:")
        for k in results['keywords']:
            kfp = os.path.join(self.project_name, 'documents', k['file_path'])
            with open(kfp, 'r', encoding='utf-8') as file:
                k_text = file.read()
                answer = self.llm_api.answer_if_possible(query, k_text)
                if answer:
                    return answer
        return None

if __name__ == "__main__":
    try:
        print("BEGIN PROGRAM")
        action = sys.argv[1]
        match action:
            case 'build':
                print('ACTION SELECTED: BUILD')
                project_name = sys.argv[2]
                base_url = sys.argv[3]

                project_settings_filepath = os.path.join(project_name, 'project_settings.json')
                if os.path.exists(project_settings_filepath):
                    raise Exception("Project Already Exists, try another action: update, search")

                print("Building Knowledge Base")
                kb = KnowledgeBase({'project_name': project_name, 'base_url': base_url})
                kb.build()

            case _:
                project_name = sys.argv[2]
                project_settings_filepath = os.path.join(project_name, 'project_settings.json')
                with open(project_settings_filepath, 'r') as file:
                    project_settings = json.load(file)
                match action:
                    case 'update':
                        print('ACTION SELECTED: UPDATE')
                        print("Loading KnowledgeBase")
                        kb = KnowledgeBase(project_settings)
                        kb.load()
                        kb.update()
                    case 'process_all':
                        print("PROCESS ALL DOCS")
                        print("Loading Knowledge Base")
                        kb = KnowledgeBase(project_settings)
                        kb.load()
                        kb.process_all_documents()

                    case 'search':
                        print('ACTION SELECTED: SEARCH')
                        query = sys.argv[3]
                        kb = KnowledgeBase(project_settings)
                        kb.load()
                        results = kb.search(query)
                        print(results)
                    case 'answer':
                        print('ACTION SELECTED: ANSWER')
                        query = sys.argv[3]
                        kb = KnowledgeBase(project_settings)
                        kb.load()
                        results = kb.answer(query)
                        print(results)


                    case _:
                        print("NO ACTION SELECTED")
                        raise Exception("Incorrect usage, please use: \npython3 knowledge-base.py build project_name base_url\npython3 knowledge-base.py load project_name\npython3 knowledge-base.py search")

    except Exception as e:
        print(e)