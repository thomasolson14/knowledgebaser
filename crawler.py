#crawler.py
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
import hashlib
import time

from document import Document

#Web Crawler 
class Crawler:
    def __init__(self, project_name, base_url):
        self.project_name = project_name
        self.base_url = base_url
        self.visited = set()
        self.blocklist = ['https://www.notion.so/help/notion.so/careers', ]

    #Check Correct Domain 
    def is_valid_url(self, url):
        for block in self.blocklist:
            if url.startswith(block):
                return False
        return url.startswith(self.base_url)

    #Gen Uid
    def id_from_url(self, url):
        sha256 = hashlib.sha256()
        sha256.update(url.encode('utf-8'))
        hash_hex = sha256.hexdigest()
        return hash_hex.lower()    

    #Visit - download or get get from saved location
    def visit(self, url, document):
        content = document.get_source()
        if content is None:
            content = self.download(document, url)
        return content
        
    #Download - get web content
    def download(self, document, url):
        retry_counter = 0
        content = None
        while content is None and retry_counter < 3:
            retry_counter += 1
            try:
                response = requests.get(url)
                time.sleep(1)
                if response.status_code == 200:
                    content = response.text
                else:
                    print(f"Failed to fetch {url}: Status code {response.status_code}")
                    print(f"Retry Counter: {retry_counter}")
              
            except Exception as e:
                print(f"Error fetching {url}: {str(e)}")
        if content is None:
            print('Download Failed. Updating Document status to ERROR')
            document.set_status('ERROR')
            raise Exception("Download Failed All Retries")
        else:
            document.set_source(content)
            document.set_status('DOWNLOADED')
            return content

    #Parse text for urls - do some cleaning 
    def extract_links(self, url, html_content):
        links = []
        soup = BeautifulSoup(html_content, 'html.parser')
        for link in soup.find_all('a', href=True):
            href = link['href']
            # Remove fragment part
            parsed_url = urlparse(href)
            cleaned_url = urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, parsed_url.params, parsed_url.query, ''))
            full_url = urljoin(url, cleaned_url)
            if self.is_valid_url(full_url):
                links.append(full_url)
        return links

    #Main method - Visit url, Extracts all links and creates new doc_file if one does not exist
    def crawl(self, url):
        if not self.is_valid_url(url):
            print(f'URL Out Of Bounds Error: {url}')
            return None, []
        doc_id = self.id_from_url(url)
        if doc_id in self.visited:
            print(f'Already visited this session: {url}')
            return doc_id, []
        doc = Document(self.project_name, doc_id)

        match doc.status:
            case 'UNVISITED':
                content = self.visit(url, doc)
            case 'ERROR':
                return doc_id, []
            case _:
                content = doc.get_source()

        self.visited.add(doc_id)

        all_links = self.extract_links(url, content)
        new_links = []
        for link in all_links:
            if self.id_from_url(link) not in self.visited:
                new_links.append(link)
        return doc_id, new_links
