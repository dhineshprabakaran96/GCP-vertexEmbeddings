from flask import Flask, request, jsonify
from langchain.text_splitter import CharacterTextSplitter
from langchain.document_loaders import PyPDFLoader
from langchain.chains import RetrievalQA
from langchain.vectorstores import Chroma
from langchain.llms import VertexAI
from langchain.embeddings import VertexAIEmbeddings

app = Flask(__name__)

llm = VertexAI(
    model_name='text-bison@001',
    max_output_tokens=256,
    temperature=0.1,
    top_p=0.8, top_k=40,
    verbose=True
)

REQUESTS_PER_MINUTE = 150
embedding = VertexAIEmbeddings(requests_per_minute=REQUESTS_PER_MINUTE)

# load document
loader = PyPDFLoader(r"/Users/DPRABAK7/Downloads/Mongodb_MongoDB test2.pdf")
documents = loader.load()

# split the documents into chunks
text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
texts = text_splitter.split_documents(documents)

# select which embeddings we want to use
embeddings = VertexAIEmbeddings(requests_per_minute=REQUESTS_PER_MINUTE)

# create the vectorstore to use as the index
# db = Chroma.from_documents(texts, embeddings)

# save to disk
# db2 = Chroma.from_documents(texts, embeddings, persist_directory="./chroma_db")

db3 = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)

# expose this index in a retriever interface
retriever = db3.as_retriever(search_type="similarity", search_kwargs={"k": 2})

# create a chain to answer questions
qa = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever, return_source_documents=True)

chat_history = []

@app.route('/ask_question', methods=['POST'])
def ask_question():
    data = request.get_json()
    user_input = data['user_input']

    result = qa({"query": user_input, "chat_history": chat_history})
    chat_history.append((user_input, result["result"]))

    return jsonify({"response": result['result']})

@app.route('/')
def home():
    return "Welcome to the QA system! Submit your question via POST request to /ask_question."

if __name__ == '__main__':
    app.run(debug=True)
