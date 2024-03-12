# %%
YOUR_OPENAI_KEY="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"
YOUR_WEAVIATE_KEY="RbZZuIxHnoxq3LpfCerCP4h4q5684PuskBEE"
YOUR_WEAVIATE_CLUSTER="https://ford-astronomer-astrobot-3tdrhgxk.weaviate.network"

# %%
"""
## 0. Install Dependencies
"""

# %%
# !pip install langchain
# !pip install weaviate-client
# !pip install openai
# !pip install unstructured
# pip install "unstructured[pdf]"

# %%
"""
## 1. Data Reading
"""

# %%
from langchain.document_loaders import DirectoryLoader

loader = DirectoryLoader('/Users/DPRABAK7/Documents/Code/Ford/LLM/data_automation/pdf_convert/converted_pdf/', glob="**/*.pdf")
data = loader.load()

# %%
print(f'You have {len(data)} documents in your data')
print(f'There are {len(data[0].page_content)} characters in your document')

# %%
"""
## 2. Text Splitting
"""

# %%
from langchain.text_splitter import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
docs = text_splitter.split_documents(data)

# %%
"""
## 3. Embedding Conversion
"""

# %%
from langchain.embeddings.openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(openai_api_key = YOUR_OPENAI_KEY)

# %%
"""
## 4. Vector Database Storage
"""

# %%
import weaviate
from langchain.vectorstores import Weaviate

# connect Weaviate Cluster
auth_config = weaviate.AuthApiKey(api_key=YOUR_WEAVIATE_KEY)

WEAVIATE_URL = YOUR_WEAVIATE_CLUSTER
client = weaviate.Client(
    url=WEAVIATE_URL,
    additional_headers={"X-OpenAI-Api-Key": YOUR_OPENAI_KEY},
    auth_client_secret=auth_config,
    startup_period=30
)

# %%
# define input structure
client.schema.delete_all()
client.schema.get()
schema = {
    "classes": [
        {
            "class": "Chatbot",
            "description": "Documents for chatbot",
            "vectorizer": "text2vec-openai",
            "moduleConfig": {"text2vec-openai": {"model": "ada", "type": "text"}},
            "properties": [
                {
                    "dataType": ["text"],
                    "description": "The content of the paragraph",
                    "moduleConfig": {
                        "text2vec-openai": {
                            "skip": False,
                            "vectorizePropertyName": False,
                        }
                    },
                    "name": "content",
                },
            ],
        },
    ]
}

client.schema.create(schema)

vectorstore = Weaviate(client, "Chatbot", "content", attributes=["source"])



# %%
# load text into the vectorstore
text_meta_pair = [(doc.page_content, doc.metadata) for doc in docs]
texts, meta = list(zip(*text_meta_pair))
vectorstore.add_texts(texts, meta)

# %%
"""
## 5. Similarity Search
"""

# %%
query = "who founded openai?"

# retrieve text related to the query
docs = vectorstore.similarity_search(query, k=4)

# %%
"""
## 6.Our Custom ChatBot
"""

# %%
from langchain.chains.question_answering import load_qa_chain
from langchain.llms import OpenAI

# define chain
chain = load_qa_chain(
    OpenAI(openai_api_key = YOUR_OPENAI_KEY,temperature=0),
    chain_type="stuff")

# create answer
chain.run(input_documents=docs, question=query)