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

LLM_MODEL = TextGenerationModel.from_pretrained("text-bison@001")

bot_email = "bmc-genapp@webex.bot"

PARAMETERS = {
  "temperature": 0.1,
  "max_output_tokens": 1024,
  "top_p": 0.8,
  "top_k": 40
}


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
  
  db3 = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
  
  retriever = db3.as_retriever(search_type="similarity", search_kwargs={"k":2})

  # create a chain to answer questions 
  qa = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever, return_source_documents=True)

  result = qa({"query": question, "chat_history": chat_history})

  chat_history = [(question, result["result"])]

  result=result["result"]

#   prompt=f"""Answer the query as truthfully as possible only using the provided context. If the answer is not contained within the text below, return answer as 'NA'. 
# The answer should be in  a well-structured and readable block of text. 
# Pay attention to formatting, such as using bullet points, numbered lists, or headers, to improve the overall readability of the text.
#   Context:-\n {result}
  
# examples:
# input: What is Tensorflow?
# output: 

# input: What is the Apigee API Publisher and how does it work?
# output: The Apigee API Publisher is a tool that allows API teams to deploy APIs to Apigee . It performs the following steps: 
#           1. Runs the provided Swagger/OpenAPI v3 API specification through the Ford API Linter and 42Crunch Audit scan 
#           2. Deploys an API proxy to the specified API gateway 
#           3. Uploads the provided Swagger/OpenAPI v3 API specification to the API Catalog .
# input: {question}
# output: 
#   """

#   print(f"This is the prompt{prompt}")

#   llm_response = LLM_MODEL.predict(   ## 5. generate response from LLM
#       prompt,
#       **PARAMETERS
#     )


#   print(llm_response)

  return result

def send_message(room_id, message_id, response_json):
  # print(suggested_list)
  # answer=response_json['result']
  CARD_PAYLOAD['body'] = CARD_PAYLOAD['body'][:4]

  default_reply="I'm sorry, I couldn't find an answer to your question. Please try rephrasing your question or ask a different question."

  # CARD_PAYLOAD['body'][1]['text'] = str(response_json.candidates[0].text) if str(response_json.candidates[0].text) != "" else default_reply
  CARD_PAYLOAD['body'][1]['text'] = str(response_json)

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
        sender_email = ""
        
        
        if data['resource'] == "messages" and data['event'] == "created":
          # Process incoming request
          message_text = ""
          
          if 'text' in data['data'].keys():
            message_text = data['data']['text']
          else:
            message_text = get_message(message_id)
          
          if 'personEmail' in data['data'].keys():
            sender_email = data['data']['personEmail']

          if sender_email == bot_email:
              return "OK"
          else:
            response_json = process_message(message_text)   
            send_message(room_id, message_id, response_json)
      else:
        return "Authentication failed!"  
    return "Message Received"         
                
        


if __name__ == '__main__':
  PORT = 6000
  app.run(debug=True, host="0.0.0.0", port=PORT)








