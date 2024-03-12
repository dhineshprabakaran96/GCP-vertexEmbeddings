from langchain_community.document_loaders import PyPDFLoader
import os
import getpass
from langchain_community.vectorstores import FAISS
from langchain_google_vertexai import VertexAIEmbeddings

loader = PyPDFLoader("/Users/DPRABAK7/Downloads/mongoDB-test-dp.pdf")
pages = loader.load_and_split()

print(pages[1])



faiss_index = FAISS.from_documents(pages, VertexAIEmbeddings())
docs = faiss_index.similarity_search("How will the community be engaged?", k=2)
for doc in docs:
    print(str(doc.metadata["page"]) + ":", doc.page_content[:300])



