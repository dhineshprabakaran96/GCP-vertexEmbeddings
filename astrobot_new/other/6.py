from langchain.document_loaders import DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain.embeddings.openai import OpenAIEmbeddings
from langchain_google_vertexai import VertexAIEmbeddings
import weaviate
from langchain.vectorstores import Weaviate
from langchain.chains.question_answering import load_qa_chain
from langchain.llms import VertexAI
from langchain.chat_models import ChatVertexAI




YOUR_PalmAPI_KEY="ya29.c.c0AY_VpZi3ty5cA_SLLVYyjW4dea8p3YE5uHGS16GaUp0DxgnRiOuoj-oBv0dDdT-tnGaD3pi6zFJNybg5IFSycHTWEzyDbN1e5wjCNd53wb2rM4YOJ8wa6Arf7TBJzBmpdt3gB2_Z-LvO-gY7Ys76yL7_41IAybvp5ZegFpf1a13tYCV5NQo5LIXf4ANZK3Cr-uuAtTqM66-THBXgrXTXyi8GrsR1EbxoKMcApVcBmiD0ryh4xGxMhKnKddYIaI16GsiJj3R6B7AqCzFhwlyynbF5C3No3BqmyZkVNbCdYUcOSow7YzBM_nwP7AyRV6Zxsz7zFN8lLCB9l4N6XRhB8ESTA7NsxD_8xCBuTgH381U0kiNbCzJQk-gHHXraUVaOu9g54PmXtfHKJ63ZyhjV2LO14OK_JlrO3gUC8rFfwOoPxLGqUChlNvcGmvijwoI2Kgv953gqsg1fZJghD1ZslQV2dLKdwnUTTOWWg4DWmJEtnRakwjBv56RFB7L_F2erlrfpufpEdhw4DzyCUKwmHMwGgvEnZMxQaVt0MgHerOAiAEDG6AKS82XuFv11Y14iSCbxE8lKXxckHxxtB_bptVlq5zMdG8dyZXDJyldq9IxezGykJSl0TvJGEFWJ0jKmJ8ozZUbRE2oGbHOl98oB7CToNUmVFSKHrRhf64PlkziIaLFdDZGHuRcjLInJEhMC96Q0i1PNQSw9crSCRf63hVq9twH739PSRFqW-jQSakdqRVwySbk0MJ5u8YsoXcdsIQtf5alsJ8QlvqtpBYxsSeX-O4fQBQBarvJ7U9XV2dUVwt7Quut8RqtF6payi2JrY7SszIaO89mwo407yzxnOIsJVZ-Xh7JB9SZUOv6se9mqjxBnmhZXhg7O54sig_pYJm-RFSBcY8W6bOZBb8M77XYm1YZRc_g3u7Qcjvw2RwsaVIU07tm134Q19gQ5ZFIs_mtt9gR7WxBQl989w2dMmiB_S-0ow3oafwpsgIXx1B0ycvy72Ykxakw"
YOUR_WEAVIATE_KEY="RbZZuIxHnoxq3LpfCerCP4h4q5684PuskBEE"
YOUR_WEAVIATE_CLUSTER="https://ford-astronomer-astrobot-3tdrhgxk.weaviate.network"
# YOUR_WEAVIATE_CLUSTER="https://ford-astronomer-astrobot-3tdrhgxk.weaviate.network"


model = VertexAI(
    model_name="text-bison@001",
    max_output_tokens=256,
    temperature=0.1,
    top_p=0.8,
    top_k=40,
    verbose=True,
)



loader = DirectoryLoader('/Users/DPRABAK7/Documents/Code/Ford/LLM/data_automation/pdf_convert/converted_pdf/', glob="**/*.pdf")
data = loader.load()


text_splitter = RecursiveCharacterTextSplitter(chunk_size=4000, chunk_overlap=0)
docs = text_splitter.split_documents(data)

embeddings = VertexAIEmbeddings()




# connect Weaviate Cluster
auth_config = weaviate.AuthApiKey(api_key=YOUR_WEAVIATE_KEY)

WEAVIATE_URL = YOUR_WEAVIATE_CLUSTER
client = weaviate.Client(
    url=WEAVIATE_URL,
    additional_headers={"X-Palm-Api-Key": YOUR_PalmAPI_KEY},
    auth_client_secret=auth_config
)

# define input structure
client.schema.delete_all()
client.schema.get()
schema = {
    "classes": [
        {
            "class": "Chatbot",
            "description": "A class called document",
            "vectorizer": "text2vec-palm",
            "moduleConfig": {
                "text2vec-palm": {
                    "projectId": "ford-4360b648e7193d62719765c7",  
                    # "apiEndpoint": "YOUR-API-ENDPOINT",
                    "modelId": "textembedding-gecko@003",
                    "titleProperty": "YOUR-TITLE-PROPERTY",
                    "vectorizeClassName": False
                }
            },
            "properties": [
                {
                    "name": "content",
                    "dataType": ["text"],
                    "description": "Content that will be vectorized",
                    "moduleConfig": {
                        "text2vec-palm": {
                            "skip": False,
                            "vectorizePropertyName": False
                        }
                    }
                }
            ]
        }
    ]
}

client.schema.create(schema)

vectorstore = Weaviate(client, "Chatbot", "content", attributes=["source"])


# load text into the vectorstore
text_meta_pair = [(doc.page_content, doc.metadata) for doc in docs]
texts, meta = list(zip(*text_meta_pair))
vectorstore.add_texts(texts, meta)

query = "what is a vectorstore?"

# retrieve text related to the query
docs = vectorstore.similarity_search(query, top_k=20)


# # define chain
# chain = load_qa_chain(
#     OpenAI(openai_api_key = "YOUR_OPENAI_KEY",temperature=0), 
#     chain_type="stuff")

model.invoke(query)



# # create answer
# chain.run(input_documents=docs, question=query)



