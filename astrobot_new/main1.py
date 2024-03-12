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

llm = VertexAI(
    model_name='text-bison@001',
    max_output_tokens=256,
    temperature=0.1,
    top_p=0.8,top_k=40,
    verbose=True,
)

REQUESTS_PER_MINUTE = 150
embeddings = VertexAIEmbeddings(requests_per_minute=REQUESTS_PER_MINUTE)

#ADFS Token credentials
Client_id= os.environ["CLIENT_ID"]
Secret=    os.environ["TERCES"]
# sa_token, expiry_time = auth.fed_token(Client_id, Secret)

conversation_ids = {}

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

BOT_ACCESS_TOKEN = os.environ["BOT_ACCESS_TOKEN"]
bot_email = "bmc-genapp@webex.bot"

INTEGRATION_ACCESS_TOKEN=os.environ["INTEGRATION_ACCESS_TOKEN"]

PROJECT_ID = "ford-4360b648e7193d62719765c7"

feedback_bq_table = "astrobot_followup_new"

LLM_MODEL = TextGenerationModel.from_pretrained("text-bison@001")

PARAMETERS = {
  "temperature": 0.1,
  "max_output_tokens": 1024,
  "top_p": 0.8,
  "top_k": 40
}

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

os.environ['no_proxy']='localhost,127.0.0.1,.ford.com,.local,.testing,.internal,.googleapis.com,19.0.0.0/8,136.1.0.0/16,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16'

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

# Message text are encrypted. So we need to make GET request by passing message ID to decrypt it
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
  
def get_message_space(message_id):
  GET_URL = "https://webexapis.com/v1/messages/" + message_id

  headers = {
      "Authorization": f"Bearer {INTEGRATION_ACCESS_TOKEN}"
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

  
def get_followup(message_id, room_id, tstamp):

  sa_token, expiry_time = auth.fed_token(Client_id, Secret)

  GET_URL = "https://webexapis.com/v1/attachment/actions/" + message_id

  headers = {
      "Authorization": f"Bearer {BOT_ACCESS_TOKEN}"
  }

  handle_proxies("SET")
  response = requests.get(GET_URL, headers=headers)

  json_data = response.json()

  # logging.info(json_data)

  session_ID=json_data['inputs']['sessionID']
  followup_question=json_data['inputs']['followup']
  conversation_ID=json_data['inputs']['conversationID']

  CARD_PAYLOAD['actions'][0]['data']['sessionID'] = session_ID
  CARD_PAYLOAD['actions'][0]['data']['conversationID'] = conversation_ID
  
  print(f"followup question: {followup_question}")
  print(f"conversation ID: {conversation_ID}")


#get_followup response from GenAPp
  url = f"https://discoveryengine.googleapis.com/v1/projects/ford-4360b648e7193d62719765c7/locations/global/collections/default_collection/dataStores/astrobot_1697723843614/conversations/{conversation_ID}:converse"

  payload = json.dumps({
    "query": {
      "input": followup_question
    },
    "summarySpec": {
      "summaryResultCount": 5,
      "ignoreAdversarialQuery": True,
      "includeCitations": True
    }
  })
  headers = {
    # 'Authorization': 'Bearer ' + auth.main(),
    'Authorization': 'Bearer ' + sa_token,
    'Content-Type': 'application/json'
  }

  response = requests.request("POST", url, headers=headers, data=payload)
  data = json.loads(response.text)

  followup_response=data['reply']['summary']['summaryText']
  followup_response=re.sub(r'\[[^\]]*\]|\([^)]*\)', '', followup_response)
  print(followup_response)

  CARD_PAYLOAD['body'][1]['text'] = followup_response

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

def get_followup_web(question, conversation_ID):

  print(conversation_ID)
  start_time = time.time()  
  sa_token, expiry_time = auth.fed_token(Client_id, Secret)
  
  followup_question=question

  print(followup_question)


  #get_followup response from GenAPp
  url = f"https://discoveryengine.googleapis.com/v1/projects/ford-4360b648e7193d62719765c7/locations/global/collections/default_collection/dataStores/astrobot_1697723843614/conversations/{conversation_ID}:converse"

  payload = json.dumps({
    "query": {
      "input": followup_question
    },
    "summarySpec": {
      "summaryResultCount": 5,
      "ignoreAdversarialQuery": True,
      "includeCitations": True
    }
  })
  headers = {
    # 'Authorization': 'Bearer ' + auth.main(),
    'Authorization': 'Bearer ' + sa_token,
    'Content-Type': 'application/json'
  }

  response = requests.request("POST", url, headers=headers, data=payload)
  data = json.loads(response.text)
  json_data = json.dumps(data)
  # logging.info(json_data)

  followup_response=data['reply']['summary']['summaryText']
  followup_response=re.sub(r'\[[^\]]*\]|\([^)]*\)', '', followup_response)
  print(followup_response)

  end_time = time.time()
  
  total_time = end_time - start_time

  # Set up the API request headers and payload

  return followup_response, total_time

def get_feedback(message_id, room_id):
  GET_URL = "https://webexapis.com/v1/attachment/actions/" + message_id

  headers = {
      "Authorization": f"Bearer {BOT_ACCESS_TOKEN}"
  }

  handle_proxies("SET")
  response = requests.get(GET_URL, headers=headers)

  json_data = response.json()

  # logging.info("feedback data")
  # logging.info(json_data)

  query = f"""UPDATE `{PROJECT_ID}.chatgpt.{feedback_bq_table}` 
SET feedback='{json_data['inputs']['feedback']}'
WHERE session_id='{json_data['inputs']['sessionID']}'"""

  logging.info(query) ## <----

  handle_proxies("UNSET")
  bigquery.Client(project = PROJECT_ID).query(query)

def get_feedback_space(message_id, room_id):
  GET_URL = "https://webexapis.com/v1/attachment/actions/" + message_id

  headers = {
      "Authorization": f"Bearer {INTEGRATION_ACCESS_TOKEN}"
  }

  handle_proxies("SET")
  response = requests.get(GET_URL, headers=headers)

  json_data = response.json()

  query = f"""UPDATE `{PROJECT_ID}.chatgpt.{feedback_bq_table}` 
SET feedback='{json_data['inputs']['feedback']}'
WHERE session_id='{json_data['inputs']['sessionID']}'"""

  logging.info(query) ## <----

  handle_proxies("UNSET")
  bigquery.Client(project = PROJECT_ID).query(query)

  # # Send thank you message after feedback is captured
  # headers = {
  #     "Authorization": f"Bearer {INTEGRATION_ACCESS_TOKEN}",
  #     "Content-Type": "application/json"
  # }
  # payload = {
  #     "roomId": room_id,
  #     "text": "Your feedback has been captured. Thank you!"
  # }

  # # Send the message to the Webex Teams API
  # handle_proxies("SET")
  # response = requests.post(
  #     "https://api.ciscospark.com/v1/messages",
  #     headers=headers,
  #     json=payload
  # )

def remove_unwanted_chars(prompt):
  string_without_unwanted_chars = prompt.replace(u'\u00A0', ' ').replace(u'\u200b', '').replace("'", "\'").replace('"', '\"')

  return string_without_unwanted_chars
  
def construct_prompt(reply_str, question):

    #If the output contains a list of steps, where each step is separated by a period and a space, format the text so that each step is on a new line. format the text so that each step is on a new line. format the text so that each step is on a new line. If the answer field contains any step by step process, format it in new line
  header = """Answer the query as truthfully as possible only using the provided context. The answer should be in JSON format which contains answer (the answer to user\'s query), id (ID of the point in the context from where the information was taken), and topic (topic from context).  If the answer is not contained within the text below, return answer as \'NA\' and \'id\' and \'topic\' as most relevant in context. Provide necessary links to the supporting documents (if present in the context). " 

  Context:-\n
  """

  context = reply_str + '\n'

  examples = """input: What is Tensorflow?
  output: {\"answer\" : \"NA\", \"id\": \"\", \"topic\": \"\"}

  input: What is Sharepoint?
  output: {\"answer\" : \"NA\", \"id\": \"KBA00527160\", \"topic\": \"SharePoint Support Information\"}

  input: What is the Apigee API Publisher and how does it work?
  output: {\"answer\" : \"The Apigee API Publisher is a tool that allows API teams to deploy APIs to Apigee . It performs the following steps: 
           1. Runs the provided Swagger/OpenAPI v3 API specification through the Ford API Linter and 42Crunch Audit scan 
           2. Deploys an API proxy to the specified API gateway 
           3. Uploads the provided Swagger/OpenAPI v3 API specification to the API Catalog .\", \"id\": \"KBA00520474\", \"topic\": \"Webex in Mobile Support Information\"}

  """

  footer = f"input: {question}\noutput: \n"
  
  return header + context + examples + footer 


def question_prompt(question):
  
  header = """Compare and contrast three different phrasings for the following inquiry, utilizing vocabulary that is distinct and creative in each instance. The output should be in JSON format which contains the three phrasings

  Context:-\n
  """

  context = question

  examples = """input: What is Tensorflow?
  output: {\"answer\" : \"NA\"}

  input: What is Sharepoint?
  output: {\"answer 1\" : \"NA\", \"answer 2\" : \"NA\", \"answer 3\" : \"NA\"}

  input: How can I request access to a GCP service that Ford doesn't currently support?


  output: {\"answer 1\": \"What is the protocol for acquiring authorization to utilize a GCP service that is not yet endorsed by Ford?\",

\"answer 2\": \"I am seeking guidance on the procedure for gaining admittance to a GCP service that is not currently sanctioned by Ford. Can you assist me?\",

\"answer 3\": \"Is there a way for me to obtain permission to utilize a GCP service that Ford currently does not endorse? If so, what would the appropriate steps be?\"}

  """

  footer = f"input: {question}\noutput: \n"

  return header + context + examples + footer

def upload_data_bq(question, format_response, response_json, cdsid, tstamp):

  # Create the unique session ID by hashing the CDSID and concatenating with the timestamp
  unique = cdsid + str(int(time.time()))
  hash_object = hashlib.sha256(unique.encode('utf-8'))
  sessionID = hash_object.hexdigest()

  CARD_PAYLOAD['actions'][0]['data']['sessionID'] = sessionID
  question=str(question)
  question=question.replace('\n', '')

  
  answer=str(format_response.candidates[0])
  answer=answer.replace('\n', '')
  print("Answer:" f'{answer}')
   
  query = f"""INSERT INTO `{PROJECT_ID}.chatgpt.{feedback_bq_table}` (cdsid, query, response, response_timestamp, session_id)
VALUES ('{cdsid}', '{question}', '{answer}', '{tstamp}', '{sessionID}')"""
  
  print(query)

  handle_proxies("UNSET")
  bigquery.Client(project = PROJECT_ID).query(query)

# Function to process incoming messages
def process_message(question):
  chat_history=[]
  # user_input = input("User Prompt: ")
  
  loader = PyPDFLoader(r"/Users/DPRABAK7/Downloads/Mongodb_MongoDB test2.pdf")
  documents = loader.load()

  text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
  texts = text_splitter.split_documents(documents)

  db2 = Chroma.from_documents(texts, embeddings, persist_directory="./chroma_db")

  # expose this index in a retriever interface
  retriever = db2.as_retriever(search_type="similarity", search_kwargs={"k":2})

  # create a chain to answer questions 
  qa = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever, return_source_documents=True)

  result = qa({"query": question, "chat_history": chat_history})
  
  chat_history = [(question, result["result"])]

  return result

# Define a function to send messages to the Webex Teams API
def send_message(room_id, message_id, response_json):
  # print(suggested_list)

  CARD_PAYLOAD['body'] = CARD_PAYLOAD['body'][:4]


  CARD_PAYLOAD['body'][1]['text'] = response_json

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
  
def send_message_space(room_id, message_id, response_json):
  CARD_PAYLOAD['body'] = CARD_PAYLOAD['body'][:4]

  
  
  CARD_PAYLOAD['body'][1]['text'] = response_json
  
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
      "Authorization": f"Bearer {INTEGRATION_ACCESS_TOKEN}",
      "Content-Type": "application/json"
  }
  payload = {
      "roomId": room_id,
      "text": "",
      "parentId": message_id,
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
  
def send_message_web(question, response_json, format_response, suggested_list):
  # print(suggested_list)

  CARD_PAYLOAD['body'] = CARD_PAYLOAD['body'][:4]

  links = {}

  for item in suggested_list:
      title = item.split('/')[-1].replace('.pdf', '')
      name = title.split(' | ')[0].split(' — ')[0].split(' - ')[0]
      print(name)
      
      if name in path:
          links[name] = f"<a href='{path[name]}' target='_blank'>{name}</a>"
 # Use the title as the key and the URL as the value
      else:
          links[name] = "https://pages.github.ford.com/gcam/astronomer-docs/" 
      # print(links[title])

  res = {
    "question": question,
    "response" : format_response if response_json == "NA" else str(format_response.candidates[0])
,
    "links": list(links.values())   # Append the links to the res dictionary
  }

  return jsonify(res)
  
def get_conversation_id(room_id):
  sa_token, expiry_time = auth.fed_token(Client_id, Secret)

  if room_id in conversation_ids:
      return conversation_ids[room_id]
  else:
      # Create Conversation history
      url="https://discoveryengine.googleapis.com/v1/projects/ford-4360b648e7193d62719765c7/locations/global/collections/default_collection/dataStores/astrobot_1697723843614/conversations"

      payload = json.dumps({
          "user_pseudo_id": room_id
      })
      headers = {
          'Authorization': 'Bearer ' + sa_token,
          'Content-Type': 'application/json'
      }

      handle_proxies("SET")
      response = requests.request("POST", url, headers=headers, data=payload)
      conversation = json.loads(response.text)
      json_data = json.dumps(conversation)
      # logging.info(json_data)
      conversation_id = conversation['name'].split("/")[-1]

      # Store conversation ID in memory
      conversation_ids[room_id] = conversation_id
      
      return conversation_id
      
# ********** Validate Incoming Request **********
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

@app.route('/astrowebhook', methods=['POST'])
def handle_webhook():
  
  data = request.get_json()
  message_text = data['data']['text']
  print(message_text)


  sender_email=""
  cdsid=""
  # webhook_name=data['name']

  if 'orgId' in data:
    webhook_name=data['name']
    room_id = data['data']['roomId']
    print("The request is from Webex")
    if 'parentId' not in data['data'].keys():

      validation, validation_msg = validate_request(request.get_data(), request.headers.get('X-Spark-Signature'))

      if validation!= True : ##<----   *****
        request_source="web"
        data = json.loads(request.data)
        # print("Question:" + data['data']['text'])

        message_id = data['data']['id']
        room_id = data['data']['roomId']
        # print(message_id)

        if data['resource'] == "messages" and data['event'] == "created":

          # Process incoming request
          message_text = ""
          if  webhook_name == "astrosupport" :
            if 'text' in data['data'].keys():
              message_text = data['data']['text']
            else:
              message_text = get_message_space(message_id)
          else:
            if 'text' in data['data'].keys():
              message_text = data['data']['text']
            else:
              message_text = get_message(message_id)

          sender_email = ""
          if 'personEmail' in data['data'].keys():
            sender_email = data['data']['personEmail'] 

          # Check if the message came from the bot, to avoid infinite loops
          if sender_email == bot_email:
              return "OK"
          
          cdsid=sender_email
          if sender_email !="chatBlueFord@webex.bot" :

            # Process the incoming message
            response_json = process_message(message_text)

            if  webhook_name == "astrosupport" :
              send_message_space(room_id, message_id, response_json)
            else:
              send_message(room_id, message_id, response_json)

          else:
              print("The input is from BMC Bot")

        elif data['resource'] == "attachmentActions" and data['event'] == "created": # If incoming request is user's feedback -> a new attachmentAction (feedback) is created
            # Process incoming feedback and upload to Bigquery using session ID
            # get_followup(message_id, room_id, data['data']['created'])
            if  webhook_name == "astrosupport_feedback" :
             get_feedback_space(message_id, room_id)
            else:
              get_feedback(message_id, room_id)

            
      else:
        return "Authentication failed!"   
  else:
    return "Authentication failed!"

  return "Message received"

if __name__ == '__main__':
  PORT = 6000
  app.run(debug=True, host="0.0.0.0", port=PORT)


