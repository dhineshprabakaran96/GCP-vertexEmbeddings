import google.generativeai as palm 
from vertexai.language_models import TextGenerationModel
from google.cloud import bigquery
from flask import Flask, request, jsonify
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

app = Flask(__name__)

#ADFS Token credentials
Client_id= os.environ["CLIENT_ID"]
Secret=    os.environ["TERCES"]

sa_token, expiry_time = auth.fed_token(Client_id, Secret)


logging.basicConfig(stream=sys.stdout, level=logging.INFO)

# palm.configure(api_key=os.environ['PALM_API_KEY'])

BOT_ACCESS_TOKEN = os.environ["BOT_ACCESS_TOKEN"]
bot_email = "bmc-genapp@webex.bot"

PROJECT_ID = "ford-4360b648e7193d62719765c7"
DATA_STORE_ID="astrobot_1697723843614"

feedback_bq_table = "astro_GCP_bot_response_feedback"

LLM_MODEL = TextGenerationModel.from_pretrained("text-bison@001")

PARAMETERS = {
  "temperature": 0.1,
  "max_output_tokens": 1000,
  "top_p": 0.8,
  "top_k": 40
}

CARD_PAYLOAD = {
    "type": "AdaptiveCard",
    "body": [
        {
            "type": "TextBlock",
            "text": "GenApp Chatbot",
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
            "title": "Ask Follow-Up ",
            "data": {
                "cardType": "input",
                "id": "inputFeedback",
                "sessionID": ""
            }
        }
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
  
def get_followup(message_id, room_id, conversation_ID):

  print(conversation_ID)

  GET_URL = "https://webexapis.com/v1/attachment/actions/" + message_id

  headers = {
      "Authorization": f"Bearer {BOT_ACCESS_TOKEN}"
  }

  handle_proxies("SET")
  response = requests.get(GET_URL, headers=headers)

  json_data = response.json()

  print(json_data)
  # followup_question=json_data['inputs']['followup']

  # logging.info("feedback data")
  # logging.info(json_data)

#   query = f"""UPDATE `{PROJECT_ID}.chatgpt.{feedback_bq_table}` 
# SET feedback='{json_data['inputs']['feedback']}', feedback_timestamp='{json_data['created']}', feedback_comment='{json_data['inputs']['followup']}'
# WHERE session_id='{json_data['inputs']['sessionID']}'"""

#   logging.info(query) ## <----

#   handle_proxies("UNSET")
#   bigquery.Client(project = PROJECT_ID).query(query)

#get_followup response from GenAPp
  # url="https://discoveryengine.googleapis.com/v1/projects/ford-4360b648e7193d62719765c7/locations/global/collections/default_collection/dataStores/astrobot_1697723843614/conversations/1743177319851951049:converse"
  url="https://discoveryengine.googleapis.com/v1/projects/ford-4360b648e7193d62719765c7/locations/global/collections/default_collection/dataStores/astrobot_1697723843614/conversations/{conversation_ID}:converse"

  headers = {

      "Authorization": f"Bearer {BOT_ACCESS_TOKEN}",
      "Content-Type": "application/json"
  }
  payload={
    "query": {
        "input": "container"
    },
    "summarySpec": {
        "summaryResultCount": 5,
        "ignoreAdversarialQuery": true,
        "includeCitations": true
    }
  }
  response = requests.request("POST", url, headers=headers, data=payload)


  # Send thank you message after feedback is captured
  
  headers = {
      "Authorization": f"Bearer {BOT_ACCESS_TOKEN}",
      "Content-Type": "application/json"
  }
  payload = {
      "roomId": room_id,
      "text": "Your followup has been captured!"
  }

  # Send the message to the Webex Teams API
  handle_proxies("SET")
  response = requests.post(
      "https://api.ciscospark.com/v1/messages",
      headers=headers,
      json=payload
  )
  
def remove_unwanted_chars(prompt):
  string_without_unwanted_chars = prompt.replace(u'\u00A0', ' ').replace(u'\u200b', '').replace("'", "\'").replace('"', '\"')

  return string_without_unwanted_chars
  
def construt_prompt(reply_str, question):

  header = """Answer the query as truthfully as possible only using the provided context. The answer should be in JSON format which contains answer (the answer to user\'s query), id (ID of the point in the context from where the information was taken), and topic (topic from context). If the answer is not contained within the text below, return answer as \'NA\' and \'id\' and \'topic\' as most relevant in context. Provide necessary links to the supporting documents (if present in the context). If the output contains a list of steps, where each step is separated by a period and a space, format the text so that each step is on a new line. format the text so that each step is on a new line. format the text so that each step is on a new line. 

  Context:-\n
  """

  context = reply_str

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

# def format_prompt():

def upload_data_bq(question, answer, cdsid, tstamp, exec_time):

  # Create the unique session ID by hashing the CDSID and concatenating with the timestamp
  unique = cdsid + str(int(time.time()))
  hash_object = hashlib.sha256(unique.encode('utf-8'))
  sessionID = hash_object.hexdigest()

  CARD_PAYLOAD['actions'][0]['data']['sessionID'] = sessionID

  query = f"""INSERT INTO `{PROJECT_ID}.chatgpt.{feedback_bq_table}` (session_id, cdsid, query, response, response_time, response_timestamp)
VALUES ('{sessionID}', '{cdsid}', '{question}', '{answer}', '{round(exec_time,3)} seconds', '{tstamp}')"""

  handle_proxies("UNSET")
  bigquery.Client(project = PROJECT_ID).query(query)

# Function to process incoming messages
def process_message(question, room_id):
  print(question)

  # start_time = time.time()
  start_time = time.time()

  print(start_time)

  #Create Conversation history
  # url="https://discoveryengine.googleapis.com/v1/projects/{PROJECT_ID}/locations/global/collections/default_collection/dataStores/{DATA_STORE_ID}/conversations"
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
  conversation_ID=conversation['name']
  conversation_ID=conversation_ID.split("/")[-1]
  print(conversation_ID)
     
  # sa_token, expiry_time = auth.fed_token(Client_id, Secret)
      
  url = "https://discoveryengine.googleapis.com/v1alpha/projects/655678175973/locations/global/collections/default_collection/dataStores/astrobot_1697723843614/conversations/-:converse"

  payload = json.dumps({
    "query": {
      "input": question
    },
    "summarySpec": {
      "summaryResultCount": 100,
      "ignoreAdversarialQuery": True,
      "includeCitations": True
    }
  })
  headers = {
    # 'Authorization': 'Bearer ' + auth.main(),
    'Authorization': 'Bearer ' + sa_token,
    'Content-Type': 'application/json'
  }
  handle_proxies("SET")
  response = requests.request("POST", url, headers=headers, data=payload)

  data = json.loads(response.text)

  # reply = data['reply']['reply']
  genapp_response = data['reply']['reply'] #Gen_App response

  # reply2 = [result["document"]["derivedStructData"]["extractive_answers"][0]["content"] for result in data["searchResults"]]   #Gen_App Extractive_Answers

  # reply_str = "\n\n".join(reply2) + "\n\n" + reply1

  genapp_response = re.sub(r'\[[^\]]*\]|\([^)]*\)', '', genapp_response)

  ##Create variations of questions using LLM

  qs_prompt=question_prompt(question)
  question_llm = LLM_MODEL.predict(qs_prompt, **PARAMETERS)
  # print(question_llm)
  question_response = json.loads(question_llm.text)
  question1, question2, question3=(json.dumps(question_response['answer 1']), question_response['answer 2'], question_response['answer 3'])
  print(question1, question2, question3)

  questions = [question1, question2, question3]
  results = [genapp_response]

  for query in questions:
      payload = json.dumps({
          "query": {
            "input": query
          },
          "summarySpec": {
            "summaryResultCount": 5,
            "ignoreAdversarialQuery": True,
            "includeCitations": True
          }
        })
      headers = {
          'Authorization': 'Bearer ' + sa_token,
          'Content-Type': 'application/json'
      }
      response = requests.request("POST", url, headers=headers, data=payload)
      data = json.loads(response.text)
      genapp_reply = data['reply']['reply']
      genapp_reply = re.sub(r'\[[^\]]*\]|\([^)]*\)', '', genapp_reply)
      extractive_answer = [result["document"]["derivedStructData"]["extractive_answers"][0]["content"] for result in data["searchResults"]] 
      extractive_answer = genapp_reply + "\n\n".join(extractive_answer)
      results.append(extractive_answer)

  print(genapp_reply)
  prompt =  construt_prompt(str(results), question) ## 4. Construct prompt
  prompt = remove_unwanted_chars(prompt)

  print("This is the prompt:" + prompt) ##

  llm_response = LLM_MODEL.predict(   ## 5. generate response from LLM
      prompt,
      **PARAMETERS
    )

  llm_data = json.loads(llm_response.text)
  # print(json.dumps(llm_data, indent=4))
  print(llm_data['answer'])


  try:
    res = eval(llm_response.text)

  except Exception as e:
    print("Error in prompt:", e)
    res = {"answer": "NA", "id": "", "topic": ""}
  
###########

#Follow-Up Question
  # headers = {
  #     "Authorization": f"Bearer {BOT_ACCESS_TOKEN}",
  #     "Content-Type": "application/json"
  # }
  # payload = {
  #     "roomId": room_id,
  #     "text": "",
  #     "attachments": [
  #       {
  #         "contentType": "application/vnd.microsoft.card.adaptive",
  #         "content": CARD_PAYLOAD
  #       }
  #     ]
  # }

  # # Send the message to the Webex Teams API
  # handle_proxies("SET")
  # response = requests.post(
  #     "https://api.ciscospark.com/v1/messages",
  #     headers=headers,
  #     json=payload
  # )

##############


  # print(reply[0])
  searchResults = []
  for item in data['searchResults']:
    searchResults.append(item['document']['derivedStructData']['link'])



  end_time = time.time()
  
  total_time = end_time - start_time
  
  # print(searchResults)
  return res, genapp_response,conversation_ID, searchResults[:3], total_time

# Define a function to send messages to the Webex Teams API
def send_message(room_id, response_json, genapp_answer, suggested_list):
  # print(suggested_list)

  CARD_PAYLOAD['body'] = CARD_PAYLOAD['body'][:4]

  for item in suggested_list:
    title = item.split('/')[-1].replace('.pdf', '')
    name = title.split(' — ')[0].split(' | ')[0]
    print(name)
    
    if name in path:
      CARD_PAYLOAD["body"].append({
            "type": "ActionSet",
            "actions": [
                {
                    "type": "Action.OpenUrl",
                    "title": item.split('/')[-1].replace('.pdf', ''),
                    "url": path[name] ## replace this URL for suggestion
                }
            ],
            "horizontalAlignment": "Left",
            "spacing": "Small"
        })
    else:
      CARD_PAYLOAD["body"].append({
            "type": "ActionSet",
            "actions": [
                {
                    "type": "Action.OpenUrl",
                    "title": "GCP Docs | Home",
                    "url":"https://docs.gcp.ford.com/docs/" ## replace this URL for suggestion
                }
            ],
            "horizontalAlignment": "Left",
            "spacing": "Small"
        })
  
  # if response_json['answer'] == 'NA' or response_json['answer'] == 'NA ':
  # # print(response_text)
  #   CARD_PAYLOAD['body'][1]['text'] = genapp_answer
  # else:
    CARD_PAYLOAD['body'][1]['text'] = response_json['answer']

  #Follow-Up
  CARD_PAYLOAD["body"].append({
      "type": "Container"
  })
  CARD_PAYLOAD["body"].append({
      "type": "TextBlock",
      "text": "Got a follow-up question ?",
      "horizontalAlignment": "Left",
      "spacing": "Large",
      "fontType": "Monospace",
      "size": "Small",
      "color": "Dark",
      "isSubtle": True,
      "separator": True
  })
  
  CARD_PAYLOAD["body"].append({
      "type": "Input.Text",
      "id": "followup",
      "placeholder": "Type your follow-up question"
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
  
  
  validation, validation_msg = validate_request(request.get_data(), request.headers.get('X-Spark-Signature'))
  # print(validation_msg)

  if validation != True : ##<----   *****
   

    data = json.loads(request.data)
    # print("Question:" + data['data']['text'])

    message_id = data['data']['id']
    room_id = data['data']['roomId']
    # print(message_id)

    conversation_ID = None

    if data['resource'] == "messages" and data['event'] == "created":
      # Process incoming request
      message_text = ""
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

      # Process the incoming message
      
      response_json, genapp_answer, conversation_ID, suggested_list, total_time = process_message(message_text, room_id)

      print(f"Total execution time: {total_time} seconds")

      upload_data_bq(message_text, response_json['answer'],  sender_email, data['data']['created'], total_time) # Upload question-answer data to bq with unique sessionID


      send_message(room_id, response_json, genapp_answer, suggested_list)
      # get_followup(message_id, room_id, conversation_ID)


    elif data['resource']== "attachmentActions" and data['event']=="created":     
       if conversation_ID is not None:
         get_followup(message_id, room_id, conversation_ID)
    
   
    
  else:
    return "Authentication failed!"

  return "Message received"

if __name__ == '__main__':
  PORT = 6000
  app.run(debug=True, host="0.0.0.0", port=PORT)


# gcloud auth application-default login    # If running in local

# export BOT_ACCESS_TOKEN=<PASTE BOT ACCESS TOKEN>
# export webhook_secret='<SECRET>'
# export ORG_ID=<CISCO ORG ID>
# export GCLOUD_ACCESS_TOKEN=<gcloud auth print-access-token>


# def format_prompt(response):
#   header = """Given a text containing a list of steps, where each step is separated by a number followed by a period and a space, 
# format the text so that each step is on a new line and followed by a number, period and space. 
#   """


#   examples = """input: What is Tensorflow?
#   output: {\"answer\" : \"NA\"}

#   input: "The Apigee API Publisher is a tool that allows API teams to deploy APIs to Apigee . It performs the following steps: 1. Runs the provided Swagger/OpenAPI v3 API specification through the Ford API Linter and 42Crunch Audit scan 2. Deploys an API proxy to the specified API gateway 3. Uploads the provided Swagger/OpenAPI v3 API specification to the API Catalog ."
#   output: "The Apigee API Publisher is a tool that allows API teams to deploy APIs to Apigee . It performs the following steps: 
#           1. Runs the provided Swagger/OpenAPI v3 API specification through the Ford API Linter and 42Crunch Audit scan 
#           2. Deploys an API proxy to the specified API gateway 
#           3. Uploads the provided Swagger/OpenAPI v3 API specification to the API Catalog ."
#   """

#   footer = f"input: {response}\noutput: \n"

#   return header  + examples + footer