#Handle both webex and web requests
import vertexai
from vertexai.language_models import TextGenerationModel
from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPIError
from flask import Flask, request, jsonify
from flask_cors import CORS
from google.cloud import logging
from path import path
import logging 
import sys
import requests
import json
import hashlib
import hmac
import os
import re
import auth
import time
import datetime
from datetime import datetime
from langchain.text_splitter import CharacterTextSplitter
from langchain.document_loaders import PyPDFLoader
from langchain.chains import RetrievalQA
from langchain.vectorstores import Chroma
from langchain.llms import VertexAI
from langchain.embeddings import VertexAIEmbeddings



app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  

BOT_ACCESS_TOKEN = os.environ["BOT_ACCESS_TOKEN"]

llm = VertexAI(
    model_name='text-bison@001',
    max_output_tokens=256,
    temperature=0.1,
    top_p=0.8,top_k=40,
    verbose=True,
)

REQUESTS_PER_MINUTE = 150
embeddings = VertexAIEmbeddings(requests_per_minute=REQUESTS_PER_MINUTE)

CARD_PAYLOAD = {
    "type": "AdaptiveCard",
    "body": [
        {
            "type": "TextBlock",
            "text": "Astrobot",
            "horizontalAlignment": "Left",
            "wrap": True,
            "fontType": "Default",
            "size": "Default",
            "weight": "Bolder",
            "color": "Accent"
        },
        {
            "type": "TextBlock",
            "text": "",
            "horizontalAlignment": "Left",
            "wrap": True,
            "fontType": "Default",
            "size": "Default",
            "weight": "Default",
            "color": "Default"
        },
        {
          "type": "Container"
        },
        {
          "type": "TextBlock",
          "text": "Here are some suggested links:",
          "horizontalAlignment": "Left",
          "wrap": True,
          "fontType": "Default",
          "size": "Default",
          "weight": "Default",
          "color": "Default"
        }
    ],
    "actions": [
        {
            "type": "Action.Submit",
            "title": "Submit Feedback",
            "data": {
                "submit": "${feedback}",
                "cardType": "input",
                "id": "inputFeedback",
                "sessionID": ""
            },
            "associatedInputs": "feedback"
        },
    ],
   
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
    "version": "1.3"
    
}

def handle_proxies(cmd):
  if cmd == "UNSET":
    # Unset proxies
    os.environ['http_proxy']=''
    os.environ['https_proxy']=''
  else:
    # Set proxies
    os.environ['http_proxy']='http://internet.ford.com:83'
    os.environ['https_proxy']='http://internet.ford.com:83'

def get_message(message_id):

  GET_URL = "https://webexapis.com/v1/messages/" + message_id

  headers = {
      "Authorization": f"Bearer {BOT_ACCESS_TOKEN}"
  }

  handle_proxies("SET")
  response = requests.get(GET_URL, headers=headers)

  if response.status_code == 200:
    # Request was successful
    json_data = response.json()
    return json_data['text']
  else:
    # Request failed, handle the error
    return 'Request failed with status code: ' + str(response.status_code)

def process_message(question):
  chat_history=[]
  # user_input = input("User Prompt: ")

  # Specify the directory path where your PDF files are located
  # folder_path = "/Users/DPRABAK7/Documents/Code/Ford/GCP/GCS/download/"

  # # List all the files in the directory
  # files = os.listdir(folder_path)

  # # Initialize an empty list to store the loaded documents
  # documents = []

  # # Iterate over the files in the directory
  # for file_name in files:
  #     if file_name.endswith(".pdf"):
  #         file_path = os.path.join(folder_path, file_name)
  #         loader = PyPDFLoader(file_path)
  #         loaded_documents = loader.load()
  #         documents.extend(loaded_documents)

  # # split the documents into chunks
  # text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
  # texts = text_splitter.split_documents(documents)

  
  # loader = PyPDFLoader(r"/Users/DPRABAK7/Downloads/Mongodb_MongoDB test2.pdf")
  # documents = loader.load()

  # text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
  # texts = text_splitter.split_documents(documents)

  # db2 = Chroma.from_documents(texts, embeddings, persist_directory="./chroma_db")
  db3 = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)


  # expose this index in a retriever interface
  retriever = db3.as_retriever(search_type="similarity", search_kwargs={"k":2})

  # create a chain to answer questions 
  qa = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever, return_source_documents=True)

  result = qa({"query": question, "chat_history": chat_history})
  
  chat_history = [(question, result["result"])]

  return result

def send_message(room_id, message_id, response_json):
  # print(suggested_list)
  answer=response_json['result']
  CARD_PAYLOAD['body'] = CARD_PAYLOAD['body'][:4]


  CARD_PAYLOAD['body'][1]['text'] = str(answer)

  CARD_PAYLOAD["body"].append({
      "type": "Container"
  })
  CARD_PAYLOAD["body"].append({
      "type": "TextBlock",
      "text": "Did the response address your needs?",
      "horizontalAlignment": "Left",
      "spacing": "Large",
      "fontType": "Monospace",
      "size": "Small",
      "color": "Dark",
      "isSubtle": True,
      "separator": True
  })
  CARD_PAYLOAD["body"].append({
      "type": "Input.ChoiceSet",
      "id" : "feedback",
      "choices": [
          {
              "title": "👍 Yes",
              "value": "yes"
          },
          {
              "title": "👎 No",
              "value": "no"
          },
          # {
          #     "title": "😑 Need Improvement",
          #     "value": "improve"
          # }
      ],
      "placeholder": "Feedback",
      "style": "expanded"
  })

  CARD_PAYLOAD["body"].insert(7,{
      "type": "Container"
  })
  CARD_PAYLOAD["body"].insert(8,{
      "type": "TextBlock",
      "text": "If you need more information, please post your queries in this thread and the team will be able to assist you.",
      "horizontalAlignment": "Left",
      "spacing": "Large",
      "wrap": True,
      "fontType": "Default",
      "size": "Default",
      "weight": "Bolder",
      "color": "Accent"
})
  # Set up the API request headers and payload
  headers = {
      "Authorization": f"Bearer {BOT_ACCESS_TOKEN}",
      "Content-Type": "application/json"
  }
  payload = {
      "roomId": room_id,
      "text": "",
      "attachments": [
        {
          "contentType": "application/vnd.microsoft.card.adaptive",
          "content": CARD_PAYLOAD
        }
      ]
  }

  # Send the message to the Webex Teams API
  handle_proxies("SET")
  response = requests.post(
      "https://api.ciscospark.com/v1/messages",
      headers=headers,
      json=payload
  )

  # Check if the request was successful
  if not response.ok:
      raise Exception("Failed to send message: {}".format(response.text))


def validate_request(raw, secret):
  
  org_id = os.environ["ORG_ID"]
  key = os.environ["webhook_secret"]

  data = json.loads(raw)
  if data['orgId'] != org_id:  # 1. Validate org ID
    return False, "Auth failed!"

  # create the SHA1 signature based on the request body JSON (raw) and our passphrase (key)
  hashed = hmac.new(key.encode(), raw, hashlib.sha1)
  validatedSignature = hashed.hexdigest()

  if validatedSignature != secret:   # 1. Validate secret
    return False, "Request not authenticated"

  return True, "Authentication passed!"


@app.route('/')
def index():
  res = {
    "response" : "Server is working fine!"
  }
  return jsonify(res)

@app.route('/cmsa/llm/new/astrowebhook', methods=['POST'])
def handle_webhook():
  data = request.get_json()
  
  if 'orgId' in data:
    webhook_name=data['name']
    room_id = data['data']['roomId']
  
    if 'parentId' not in data['data'].keys():

      validation, validation_msg = validate_request(request.get_data(), request.headers.get('X-Spark-Signature'))
      if validation!= True : ##<----   *****
        request_source="web"
        data = json.loads(request.data)
        # print("Question:" + data['data']['text'])

        message_id = data['data']['id']
        room_id = data['data']['roomId']
        if data['resource'] == "messages" and data['event'] == "created":
          # Process incoming request
          message_text = ""
          
          if 'text' in data['data'].keys():
            message_text = data['data']['text']
          else:
            message_text = get_message(message_id)
          
          response_json = process_message(message_text)   
          send_message(room_id, message_id, response_json)
      else:
        return "Authentication failed!"  
    return "Message Received"         
                
        


if __name__ == '__main__':
  PORT = 6000
  app.run(debug=True, host="0.0.0.0", port=PORT)








