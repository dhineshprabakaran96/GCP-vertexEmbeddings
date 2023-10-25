import vertexai
from vertexai.preview.language_models import TextEmbeddingModel
from google.cloud import storage
from google.cloud import bigquery
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
import pandas as pd
import requests
import os
import json
import math
import re

project_id = 'ford-4360b648e7193d62719765c7'
matching_engine_projectid = "ford-071510988cc8f3cc7b39d2d8"
client = bigquery.Client(project=project_id)
EMBEDDING_MODEL = TextEmbeddingModel.from_pretrained("textembedding-gecko@001")

schema = [
    bigquery.SchemaField('id', 'INTEGER'),
    bigquery.SchemaField('article_title', 'STRING'),
    bigquery.SchemaField('answer', 'STRING'),
    bigquery.SchemaField('kba_id', 'STRING')
]

# Create the table if it does not exist
table_name = 'aharshit-test'    # <------ Change bucket name
table_ref = client.dataset('chatgpt').table(table_name)
table = bigquery.Table(table_ref, schema=schema)
table = client.create_table(table, exists_ok=True)

app = Flask(__name__)

# Define the URLs for token generation and data access
TOKEN_URL = 'https://ford-restapi.onbmc.com/api/jwt/login'
DATA_URL = """https://ford-restapi.onbmc.com/api/arsys/v1/entry/RKM:HowToTemplate_Manageable_Join?q=('InternalUse'="No")"""

# Set and unset proxies in runtime 
def handle_proxies(cmd):
  if cmd == "UNSET":
    # Unset proxies
    os.environ['http_proxy']=''
    os.environ['https_proxy']=''
  else:
    # Set proxies
    os.environ['http_proxy']='http://internet.ford.com:83'
    os.environ['https_proxy']='http://internet.ford.com:83'

# Function to get access token
def get_access_token():
  username = os.environ['username']
  password = os.environ['password']
  access_token = ""
  payload=f'username={username}&password={password}'
  headers = {
    'Content-Type': 'application/x-www-form-urlencoded'
  }
  
  handle_proxies("SET")
  response = requests.request("POST", TOKEN_URL, headers=headers, data=payload)
  if response.status_code == 200:
    access_token = response.text
  
  return access_token, response.status_code

# Function to get BMC data
def get_bmc_data(access_token):
  payload={}
  headers = {
    'Authorization': f'AR-JWT {access_token}'
  }

  handle_proxies("SET")
  response = requests.request("GET", DATA_URL, headers=headers, data=payload)
  return response.json(), response.status_code


# Get the last ID in the table
def get_last_id():
  last_id = 0
  num_rows = 0

  handle_proxies("UNSET")
  table = client.query(f'SELECT COUNT(*) AS num_rows FROM `{table_ref}`').result()
  for item in table:
    num_rows = item[0]

  # print(num_rows)
  if num_rows == 0:
    print('The table is empty')
  else:
    print(f'The table has {num_rows} rows')
    query = f'SELECT MAX(id) FROM `{table_ref}`'
    table1 = client.query(query).result()
    for item in table1:
      last_id = item[0]

  return int(last_id)

# Insert data into the table
def insert_data(last_id, article_title, answer, kba_id):

  handle_proxies("UNSET")
  row_to_insert = (last_id, article_title, answer, kba_id)
  errors = client.insert_rows(table, [row_to_insert])
  if errors:
    print(f'Encountered errors while inserting rows: {errors}')

  print("Successfully inserted data with ID: ", last_id)


def generate_answer(input_str):
  soup = BeautifulSoup(input_str, 'html.parser')

  output_str = ""
  for li in soup.find_all('li'):
      text = li.text.strip()
      link = li.find('a')
      if link is not None:
          href = link.get('href')
          text += f" ({href})"
      output_str += text + "\n\n"

  return output_str.strip().replace("\n", " ")

def generate_answer_2(raw_data):
  output_str = ""
  skip = 0
  for i in range(len(raw_data)):
      if raw_data[i] == '<':
          skip += 1
      elif raw_data[i] == '>':
          skip -= 1
      elif skip == 0:
          output_str += raw_data[i]

  return output_str.strip().replace("&nbsp;", " ").replace("\n", " ").replace("&#39;", "'")

# Upload data to bigquery
def bq_upload(data):
  last_id = get_last_id() 
  
  for item in data['entries'][:10]:

    kba_id = item["values"]["DocID"]
    article_title = item["values"]["ArticleTitle"]
    answer = ""
    try: 
      soup = BeautifulSoup(item["values"]["RKMTemplateAnswer"], 'html.parser')

      if len(soup.find_all('li'))>0:
        answer = generate_answer(item["values"]["RKMTemplateAnswer"])
      else:
        answer = generate_answer_2(item["values"]["RKMTemplateAnswer"])

      answer = re.sub(r'\(javascript:.*?\}\)', '', answer) #Remove javascript substrings
    
    except TypeError:
      print("some error in - ", kba_id)

    if len(answer)>0:
      # Insert into Bigquery
      last_id = last_id + 1
      insert_data(str(last_id), article_title, answer, kba_id)

def get_embedding(questions):

  handle_proxies("UNSET")
  vertexai.init(project = project_id, location = "us-central1")
  # handle_proxies("SET")

  emb_results = EMBEDDING_MODEL.get_embeddings(questions)
  result = []
  for embedding in emb_results:
    result.append(embedding.values)

  return result

# Create Embeddings and store it to GCS
def create_emb():
  handle_proxies("UNSET")
  query = f"SELECT * FROM `{table_ref}`"
  rows = client.query(query).result()
  df = rows.to_dataframe()

  ids = df.id.tolist()
  answer = df.answer.tolist()
  title = df.article_title.tolist()

  for i in range(0, len(answer)):
    answer[i] = "Topic: " + title[i] + "\n\n" + answer[i]

  batch_size = 5  

  for i in range(0, len(ids), batch_size):
    nth_batch = i+batch_size
    if i+batch_size > len(ids):
      nth_batch = len(ids)-1

    id_batch = ids[i:nth_batch]
    emb_batch = answer[i:nth_batch]
    print("Creating embeddings : ", math.ceil((i/len(ids))*100) , "%")
    emb_list = get_embedding(emb_batch) 

    with open("embeddings.json", 'a') as f1:
      embeddings_formatted = []
      for j in range(0, len(emb_list)):
        embeddings_formatted.append(json.dumps( 
          {
            "id" : str(id_batch[j]),
            "embedding" : emb_list[j]
          }
        ) + "\n")
      f1.writelines(embeddings_formatted)

  print("Embeddings created")


access_token, status_code = get_access_token() # Task 0 : Get BMC access token
data, status_code = get_bmc_data(access_token)  # Task 1 : Get BMC data
bq_upload(data) # Task 2 : upload data to bq
create_emb() # Task 3 : Create Embeddings and store in local 



# gcloud auth application-default login
# Set env variables : "username" and "password" 
# Change Table name
# Upload Embeddings.json to gcs