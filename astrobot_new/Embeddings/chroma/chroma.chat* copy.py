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

chat_history = []
documents = None

@app.route('/upload_document', methods=['POST'])
def upload_document():
    global documents

    data = request.get_json()
    document_path = data['document_path']

    loader = PyPDFLoader(document_path)
    documents = loader.load()

    return jsonify({"message": "Document uploaded successfully"})

@app.route('/ask_question', methods=['POST'])
def ask_question():
    global documents
    data = request.get_json()
    user_input = data['user_input']

    if documents is None:
        return jsonify({"error": "No document uploaded. Please upload a document first."})

    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    texts = text_splitter.split_documents(documents)

    embeddings = VertexAIEmbeddings(requests_per_minute=REQUESTS_PER_MINUTE)

    db = Chroma.from_documents(texts, embeddings)
    retriever = db.as_retriever(search_type="similarity", search_kwargs={"k": 2})

    qa = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever, return_source_documents=True)

    result = qa({"query": user_input, "chat_history": chat_history})
    chat_history.append((user_input, result["result"]))

    return jsonify({"response": result['result']})

@app.route('/')
def home():
    return "Welcome to the QA system! Use /upload_document to upload a document and /ask_question to query the uploaded document."

if __name__ == '__main__':
    app.run(debug=True)
