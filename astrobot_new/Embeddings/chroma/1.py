from langchain.text_splitter import CharacterTextSplitter
from langchain.document_loaders import PyPDFLoader
from langchain.chains import RetrievalQA
from langchain.vectorstores import Chroma

from langchain.llms import VertexAI
from langchain.embeddings import VertexAIEmbeddings
from vertexai.language_models import TextEmbeddingModel

model = TextEmbeddingModel.from_pretrained("textembedding-gecko@001")


llm = VertexAI(
    model_name='text-bison@001',
    max_output_tokens=256,
    temperature=0.1,
    top_p=0.8,top_k=40,
    verbose=True,
)

REQUESTS_PER_MINUTE = 150
embedding = VertexAIEmbeddings(requests_per_minute=REQUESTS_PER_MINUTE)

# load document
loader = PyPDFLoader(r"Astro_FAQ's.pdf")
documents = loader.load()

# split the documents into chunks
text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
texts = text_splitter.split_documents(documents)

# # select which embeddings we want to use
# embeddings = VertexAIEmbeddings(requests_per_minute=REQUESTS_PER_MINUTE)

# create the vectorestore to use as the index
db = Chroma.from_documents(texts, embedding)

# expose this index in a retriever interface
retriever = db.as_retriever(search_type="similarity", search_kwargs={"k":2})

# create a chain to answer questions 
qa = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever, return_source_documents=True)