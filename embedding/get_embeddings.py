import os
import numpy as np
import openai
import pandas as pd

# openai.api_key = os.getenv("OPENAI_API_KEY")

openai.api_version = '2022-12-01'
openai.api_base = 'https://ito-openai-instance.openai.azure.com/' # Please add your endpoint here
openai.api_type = 'azure'
openai.api_key = os.getenv("OPENAI_API_KEY")  # Please add your api key here

COMPLETIONS_MODEL = "deployment-851fdef5eaf64d8191f5d5270cadda4d"
EMBEDDING_MODEL = "deployment-d38e46e6d5924a478a5c744a409a48d4"

def print_output(document_embeddings):
  document_keys = list(document_embeddings.keys())
  location = "./output/document_embedding.csv"
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

df = pd.read_csv('./input/results.csv')
df = df.set_index(["title", "heading"])

document_embeddings = compute_doc_embeddings(df)

print_output(document_embeddings)
