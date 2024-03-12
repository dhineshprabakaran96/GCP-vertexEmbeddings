from langchain.text_splitter import CharacterTextSplitter
from langchain.document_loaders import PyPDFLoader
from langchain.chains import RetrievalQA
from langchain.vectorstores import Chroma

from langchain.llms import VertexAI
from langchain.embeddings import VertexAIEmbeddings
import glob


llm = VertexAI(
    model_name='text-bison@001',
    max_output_tokens=256,
    temperature=0.1,
    top_p=0.8, top_k=40,
    verbose=True,
)

REQUESTS_PER_MINUTE = 150
embedding = VertexAIEmbeddings(requests_per_minute=REQUESTS_PER_MINUTE)

# List of document file paths
# document_paths = ["/path/to/document1.pdf", "/path/to/document2.pdf", "/path/to/document3.pdf"]
# document_paths= ["/Users/DPRABAK7/Documents/Ford_Docs/Astro_Faq's.pdf", "/Users/DPRABAK7/Downloads/WLW Diet Sheet_1-8 Pages.pdf"]
document_directory = "/Users/DPRABAK7/Documents/Code/Ford/GCP/GCS/astrodocs/astrobot/*.pdf"
document_paths = glob.glob(document_directory)



# Load and process each document
texts = []
for path in document_paths:
    loader = PyPDFLoader(path)
    documents = loader.load()
    
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    texts.extend(text_splitter.split_documents(documents))

# select which embeddings we want to use
embeddings = VertexAIEmbeddings(requests_per_minute=REQUESTS_PER_MINUTE)

# create the vectorestore to use as the index
# db = Chroma.from_documents(texts, embeddings)

db2 = Chroma.from_documents(texts, embeddings, persist_directory="./chroma_db")

# expose this index in a retriever interface
retriever = db2.as_retriever(search_type="similarity", search_kwargs={"k": 2})

# create a chain to answer questions
qa = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever, return_source_documents=True)

chat_history = []
user_input = input("User Prompt: ")

while user_input.lower() != 'bye':
    result = qa({"query": user_input, "chat_history": chat_history})
    print(f"User: {user_input}")
    print(f"Bot: {result['result']}\n")
    chat_history = [(user_input, result["result"])]
    user_input = input("User Prompt: ")
