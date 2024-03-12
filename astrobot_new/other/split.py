from langchain_community.document_loaders import PyPDFLoader
import os
import getpass
from langchain_community.vectorstores import FAISS
from langchain_google_vertexai import VertexAIEmbeddings





loader = PyPDFLoader("/Users/DPRABAK7/Documents/Code/Ford/LLM/ITO-ChatGPT/astrobot_new/sample_docs/Astro_Faq's.pdf")
pages = loader.load_and_split()

pages[0]


faiss_index = FAISS.from_documents(pages, VertexAIEmbeddings())
docs = faiss_index.similarity_search("current tag not changing", k=2)
for doc in docs:
    print(str(doc.metadata["page"]) + ":", doc.page_content[:300])



