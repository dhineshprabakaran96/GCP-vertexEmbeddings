# import
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_community.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddings,
)
from sentence_transformers import SentenceTransformer

from langchain_community.vectorstores import Chroma
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from vertexai.language_models import TextEmbeddingModel


from getpass import getpass
import os
import chromadb


# load the document and split it into chunks
loader = TextLoader("/Users/DPRABAK7/Documents/Code/state_of_the_union.txt")
documents = loader.load()

# split it into chunks
text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
docs = text_splitter.split_documents(documents)

# create the open-source embedding function
embeddings = SentenceTransformer('embedding-data/deberta-sentence-transformer')




# print(embeddings)

# load it into Chroma
db = Chroma.from_documents(docs, embeddings)

# query it
query = "What did the president say about Ketanji Brown Jackson"
docs = db.similarity_search(query)

# print results
# print(docs[0].page_content)


# save to disk
db2 = Chroma.from_documents(docs, embeddings, persist_directory="./chroma_db")
docs = db2.similarity_search(query)

# load from disk
db3 = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
docs = db3.similarity_search(query)
# print(docs[0].page_content)

