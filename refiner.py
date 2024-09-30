#refiner.py
import re
from bs4 import BeautifulSoup
from document import Document

from llm_api import llmAPI

#Refine webpage data into vectors for search
class Refiner():
    def __init__(self, project_name):
        self.project_name = project_name
        self.llm_api = llmAPI()

    #Process document - trim, chunk, create metadata for vectors
    def process(self, doc_id):
        doc = Document(self.project_name, doc_id)

        match doc.status:
            case 'ERROR':
                print('STATUS IN ERROR')
                return None
            case 'DOWNLOADED':
                print("status: DOWNLOADED")
                self.trim(doc)
                self.chunk(doc)
                return None
            case 'CHUNKED':
                print("status: CHUNKED")
                to_index = self.evaluate(doc)
                return to_index
            case 'PROCESSED':
                return doc.get_vectors()
            case _:
                print('unkown status')

    #Trim html garbage with BeautifulSoup
    def trim(self, document):
        print(f"Trimming Doc: {document.doc_id}")
        source = document.get_source()
        soup = BeautifulSoup(source, 'html.parser')

        content = []
        title = soup.find('title')
        if title and title.text:
            content.append(f'h1: {title.text}')

        # Remove <header> elements
        for mal in soup.find_all(['script','header', 'footer', 'nav', 'meta']):
            mal.decompose()

        elements = soup.body

        for element in elements.descendants:
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                content.append(f"\n{element.name}: {element.get_text(strip=True)}\n")
            elif element.name == 'p':
                text = element.get_text(strip=True)
                if text:
                    content.append(f'{text} ')
            elif element.name == 'blockquote':
                quote = element.get_text(strip=True)
                content.append(f"> {quote}\n")
            elif element.name in ['ul', 'ol']:
                if 'class' not in element:
                    list_items = [li.get_text(strip=True) for li in element.find_all('li')]
                    if list_items:
                        content.append('\n'.join([f"- {item}" for item in list_items]) + '\n')
                else:
                    _class = element['class'][0]
                    if 'nav' not in _class and 'learnMoreSection' not in _class:
                        list_items = [li.get_text(strip=True) for li in element.find_all('li')]
                        if list_items:
                            content.append('\n'.join([f"- {item}" for item in list_items]) + '\n')
            elif element.name == 'table':
                table_text = self.convert_table_to_markdown(element)
                if table_text:
                    content.append(table_text + '\n')


            full_text = '\n'.join(content)

        # Clean up excessive whitespace
        full_text = re.sub(r'\n\s*\n', '\n\n', full_text)
        trimmed = full_text.strip()

        document.set_trimmed(trimmed)
        document.set_status('TRIMMED')

        print(trimmed)
        return trimmed;
    #ChatGPTed html to markdown for tables.
    def convert_table_to_markdown(self, table):
        markdown = []
        headers = []
        rows = []

        # Extract table headers
        header_row = table.find('tr')
        if not header_row:
            return ""

        th_tags = header_row.find_all('th')
        if th_tags:
            headers = [th.get_text(strip=True) for th in th_tags]
            rows = table.find_all('tr')[1:]  # Exclude header row
        else:
            # If there are no <th>, treat first row as headers
            td_tags = header_row.find_all('td')
            headers = [td.get_text(strip=True) for td in td_tags]
            rows = table.find_all('tr')[1:]

        if not headers:
            return ""

        # Create Markdown header
        header_md = '| ' + ' | '.join(headers) + ' |'
        separator_md = '| ' + ' | '.join(['---'] * len(headers)) + ' |'
        markdown.append(header_md)
        markdown.append(separator_md)

        # Add table rows
        for row in rows:
            cells = row.find_all(['td', 'th'])
            row_data = [cell.get_text(strip=True) for cell in cells]
            row_md = '| ' + ' | '.join(row_data) + ' |'
            markdown.append(row_md)

        # Combine all parts
        return '\n'.join(markdown)

    #chunk data by headers - create small, medium and large chunksizes
    def chunk(self, document):
        print("CHUNKING")
        trimmed = document.get_trimmed()
        paragraphs = re.split(r'\n\s*\n+', trimmed.strip())

        sections = {'h1': [], 'h2': [], 'h3': []}

        for p in paragraphs:
            p.join('\n')
            if p.startswith('h1:'):
                sections['h1'].append([p])
                sections['h2'].append([])
                sections['h3'].append([])
            elif p.startswith('h2:'):
                sections['h1'][-1].append(p)
                sections['h2'].append([p])
                sections['h3'].append([])
            elif p.startswith('h3:'):
                sections['h1'][-1].append(p)
                sections['h2'][-1].append(p)
                sections['h3'].append([p])
            else:
                sections['h1'][-1].append(p)
                sections['h2'][-1].append(p)
                sections['h3'][-1].append(p)
        chunks = {}

        for size in sections.keys():
            sections[size] = [ele for ele in sections[size] if ele != []]
            for chunk_list in sections[size]:
                chunk = ''.join(chunk_list)
                if size in chunks:
                     chunks[size].append(chunk)
                else:
                     chunks[size] = [chunk]
        document.set_raw_chunks(chunks)
        document.set_status('CHUNKED')
        self.prettify_chunks(document)

    #remove typos, ect
    def prettify_chunks(self, document):
        print("PRETTIFY")
        pretty_chunks = {}
        raw_chunks = document.get_raw_chunks()
        for size in raw_chunks.keys():
            print(size)
            pretty_chunks[size] = []
            for chunk in raw_chunks[size]:
                pc = self.llm_api.prettify(chunk)
                print(pc)
                pretty_chunks[size].append(pc)

        document.set_pretty_chunks(pretty_chunks)
        return pretty_chunks

    #Generate metadata - create new blocks organized by relevancy to potential user searches.
    #Reterns vectors grouped by type, pointing to the lcation of associated information
    def evaluate(self, document):
        print("EVALUATE")
        
        pretty_chunks = document.get_pretty_chunks()
        topics = []
        user_questions = []
        keyword_vectors = []

        #Extract Metadata from Big Chunk
        for i in range(0, len(pretty_chunks['h1'])):
            print(i)
            big_chunk = pretty_chunks['h1'][i]
            topic = big_chunk.split('\n')[0]
            if topic.startswith('h1:'):
                topic = topic[3:].strip()
            topics.append(topic)

            qs = self.llm_api.generate_potential_questions(big_chunk)
            user_questions.extend(qs)

            keywords = self.llm_api.generate_keywords(big_chunk)

            for kw in keywords:
                keyword_vectors.append({'keyword': kw, 'filepath': document.doc_id + '/chunks/pretty/h1/' + f'{i}.txt'})

        topic_vectors = []
        for i in range(0, len(topics)):
            topic_vectors.append({'topic': topics[i], 'filepath': document.doc_id + '/chunks/pretty/h1/' + f'{i}.txt'})

        synthetic_chunks = []

        relevancy_threshold = 8

        to_evaluate = []
        if 'h3' in pretty_chunks:
            to_evaluate.extend(pretty_chunks['h3'])
        if 'h2' in pretty_chunks:
            to_evaluate.extend(pretty_chunks['h2'])
        if 'h1' in pretty_chunks:
            to_evaluate.extend(pretty_chunks['h1'])

        counter = len(user_questions) * len(to_evaluate)

        for q in user_questions:
            print(f"Countdown counter: {counter}")
            relevant_chunks = []

            for chunk in to_evaluate:
                relevancy_score = self.llm_api.evaluate_relevance(q, chunk)
                counter-=1
                if relevancy_score > 0:
                    relevant_chunks.append((chunk, relevancy_score))
                if relevancy_score >= relevancy_threshold:
                    break;

            synthetic_chunk = "" + q + "\n"
            
            relevant_chunks.sort(reverse=True, key=lambda x: x[1])
            total_score = 0
            for chunk in relevant_chunks:
                if total_score < relevancy_threshold:
                    synthetic_chunk += chunk[0]
                    total_score += chunk[1]

            synthetic_chunks.append({'question': q, 'text' : synthetic_chunk})

        document.save_synthetic_chunks(synthetic_chunks)


        question_vectors = []
        for i in range(0, len(user_questions)):

            question_vectors.append({'question':user_questions[i], 'filepath': document.doc_id + f'/chunks/synthetic/{i}.json'})


        document.set_status('PROCESSED')
        to_index = {'topics': topic_vectors, 'keywords': keyword_vectors, 'questions': question_vectors}
        print(f"TO_INDEX:{to_index}")
        return to_index











