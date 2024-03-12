from langchain.vectorstores.weaviate import Weaviate
import weaviate
from langchain.embeddings import OpenAIEmbeddings
import os

# auth_config = weaviate.auth.AuthApiKey(api_key=os.environ.get('RbZZuIxHnoxq3LpfCerCP4h4q5684PuskBEE'))
auth_config = "RbZZuIxHnoxq3LpfCerCP4h4q5684PuskBEE"
client = weaviate.Client(
    url="https://ford-astronomer-astrobot-3tdrhgxk.weaviate.network",
    auth_client_secret=auth_config,
    additional_headers={
        "X-OpenAI-Api-Key": os.environ.get('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')
    }
)

# We need to set index_name and vectorizer for the database, 
# otherwise we will not be able to measure text similarities
# langchain is supposed to set this for you, add this if needed
# You just need to do it the very first time setting the class
class_obj = {
    "class": "LangChain",
    "vectorizer": "text2vec-openai",
}

try:
  # Add the class to the schema
  client.schema.create_class(class_obj)
except:
  print("Class already exists")

embeddings = OpenAIEmbeddings()
# I use 'LangChain' for index_name and 'text' for text_key
vectorstore = Weaviate(client, "LangChain", "text", embedding=embeddings)