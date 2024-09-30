# knowledgebaser

## Use
Create a Knowledge base from a base url
  -Crawls web, downloads pages
  -Trims and Chunks content
  -Synthesizes/organizes content into blocks by possible queries
  -Searchs with kNN in vectorDB
  -Answers questions with RAG style
  
CLI usage: 
  Before first use, install packages, `export OPENAI_API_KEY='your-key'`

  BUILD - builds project
  
    python3 knowledge_base.py build project_name base_url
    
  PROCESS_ALL - adds all documents to the to_process queue and starts
  
    python3 knowledge_base.py process_all project_name
    
  SEARCH - returns relevant chunks
  
    python3 knowledge_base.py search project_name query
    
  ANSWER - answers question using retrieved chunk augmentation
  
    python3 knowledge_base.py build project_name query

Project will take a while to build because it needs to crawl, refine data and build index.
