import os
import numpy as np
import openai
import pandas as pd
import configparser

# create a ConfigParser object
config = configparser.ConfigParser()
# read the configuration file
config.read('/config.ini')

#openai.api_key = os.getenv("OPENAI_API_KEY")


# Use the new environment variable
key = config['openAI']['Azure_OPENAI_API_KEY']
#print(openai.api_key)


openai.api_version = '2022-12-01'
openai.api_base = 'https://ito-openai-instance.openai.azure.com/' # Please add your endpoint here
openai.api_type = 'azure'
#openai.api_key = os.getenv("OPENAI_API_KEY")  # Please add your api key here
openai.api_key = key  # Please add your api key here

COMPLETIONS_MODEL = "deployment-851fdef5eaf64d8191f5d5270cadda4d"
EMBEDDING_MODEL = "deployment-d38e46e6d5924a478a5c744a409a48d4"

def print_output(document_embeddings):
  document_keys = list(document_embeddings.keys())
  location = "./vector_df.csv"
  length_vectors = len(document_embeddings[document_keys[0]])
  with open(location, 'w') as file:
    # Print Header
    file.write("title,heading,")
    for i in range(1, length_vectors):
      file.write("%d,"%(i))
    file.write("%d\n"%(length_vectors))

    # Print Contents  
    for items in document_keys:
      file.write("%s,%s,"%(items[0],items[1]))
      for i in range(1, length_vectors):
        file.write("%f,"%(document_embeddings[items][i-1]))
      file.write("%f\n"%(document_embeddings[items][length_vectors-1]))
    print("Embedding output saved to location: ", location)

def get_embedding(text):
    os.environ['http_proxy']='http://internet.ford.com:83'
    os.environ['https_proxy']='http://internet.ford.com:83'
    result = openai.Embedding.create(
      deployment_id=EMBEDDING_MODEL,
      input=text
    )
    return result["data"][0]["embedding"]

def compute_doc_embeddings(df):
    # Create an embedding for each row in the dataframe using the OpenAI Embeddings API.
    # Return a dictionary that maps between each embedding vector and the index of the row that it corresponds to.
    return {
        idx: get_embedding(r.content) for idx, r in df.iterrows()
    }

df = pd.read_csv('./tokenized_data.csv')
df = df.set_index(["title", "heading"])
#print(df)
document_embeddings = compute_doc_embeddings(df)

print_output(document_embeddings)


