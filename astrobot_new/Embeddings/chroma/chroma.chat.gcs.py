import os
from google.cloud import storage
from langchain.text_splitter import CharacterTextSplitter
from langchain.document_loaders import PyPDFLoader
from langchain.chains import RetrievalQA
from langchain.vectorstores import Chroma
from langchain.llms import VertexAI
from langchain.embeddings import VertexAIEmbeddings

# Specify your GCP project name
project_name = 'ford-4360b648e7193d62719765c7'

# Initialize a client with the specified project
client = storage.Client(project=project_name)

# Define your GCS bucket name and directory
bucket_name = 'chatgpt_data_source'
directory_name = 'Mongodb'


# Get the bucket
bucket = client.get_bucket(bucket_name)

# List to store loaded documents
documents = []

# Iterate over the blobs/files in the specified directory
blobs = bucket.list_blobs(prefix=directory_name, delimiter='/')
for blob in blobs:
    if blob.name.endswith('/'):
        continue  # Skip directories

    # Create the local directory structure to match GCS directory
    local_file_path = os.path.join('.', blob.name)
    os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

    # Download the file to the local directory
    blob.download_to_filename(local_file_path)

    # Load the downloaded file using PyPDFLoader or any other method you have
    loader = PyPDFLoader(local_file_path)
    loaded_documents = loader.load()
    documents.extend(loaded_documents)

llm = VertexAI(
    model_name='text-bison@001',
    max_output_tokens=256,
    temperature=0.1,
    top_p=0.8,top_k=40,
    verbose=True,
)

# split the documents into chunks
text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
texts = text_splitter.split_documents(documents)

# select which embeddings we want to use
REQUESTS_PER_MINUTE = 150
embeddings = VertexAIEmbeddings(requests_per_minute=REQUESTS_PER_MINUTE)

db = Chroma.from_documents(texts, embeddings)

retriever = db.as_retriever(search_type="similarity", search_kwargs={"k":2})

# create a chain to answer questions 
qa = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever, return_source_documents=True)

chat_history = []
user_input = input("User Prompt: ")

while user_input != ['Bye', 'bye']:
    result = qa({"query": user_input, "chat_history": chat_history})
    print(f"User: {user_input}")
    print(f"Bot: {result['result']}\n")
    chat_history = [(user_input, result["result"])]
    user_input = input("User Prompt: ")