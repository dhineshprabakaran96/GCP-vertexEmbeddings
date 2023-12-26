#Handle both webex and web requests

import vertexai
from vertexai.language_models import TextGenerationModel
from vertexai.preview.generative_models import GenerativeModel, ChatSession
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

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  

#ADFS Token credentials
Client_id= os.environ["CLIENT_ID"]
Secret=    os.environ["TERCES"]
# sa_token, expiry_time = auth.fed_token(Client_id, Secret)

conversation_ids = {}

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

BOT_ACCESS_TOKEN = os.environ["BOT_ACCESS_TOKEN"]
bot_email = "bmc-genapp@webex.bot"

PROJECT_ID = "ford-4360b648e7193d62719765c7"

feedback_bq_table = "astrobot_followup_new"

# LLM_MODEL = TextGenerationModel.from_pretrained("text-bison@001")
LLM_MODEL=model = GenerativeModel("gemini-pro")

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
                "sessionID": "",
                "conversationID": ""
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
  
def get_followup(message_id, room_id, tstamp):

  sa_token, expiry_time = auth.fed_token(Client_id, Secret)

  GET_URL = "https://webexapis.com/v1/attachment/actions/" + message_id

  headers = {
      "Authorization": f"Bearer {BOT_ACCESS_TOKEN}"
  }

  handle_proxies("SET")
  response = requests.get(GET_URL, headers=headers)

  json_data = response.json()

  logging.info(json_data)

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

  # query = f"""INSERT INTO `{PROJECT_ID}.chatgpt.{feedback_bq_table}` (session_id, cdsid, conversation_id, query, response, response_timestamp)
  # VALUES ('{session_ID}', '{cdsid}', '{cdsid}','{followup_question}', '{followup_response}', '{tstamp}')"""

  # handle_proxies("UNSET")
  # bigquery.Client(project = PROJECT_ID).query(query)

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
  logging.info(json_data)

  followup_response=data['reply']['summary']['summaryText']
  followup_response=re.sub(r'\[[^\]]*\]|\([^)]*\)', '', followup_response)
  print(followup_response)

  end_time = time.time()
  
  total_time = end_time - start_time

  # query = f"""INSERT INTO `{PROJECT_ID}.chatgpt.{astrobot_followup_web}` (session_id, cdsid, conversation_id, query, response, response_timestamp)
  # VALUES ('{session_ID}', '{cdsid}', '{cdsid}','{followup_question}', '{followup_response}', '{tstamp}')"""

  # handle_proxies("UNSET")
  # bigquery.Client(project = PROJECT_ID).query(query)

  # Set up the API request headers and payload

  return followup_response, total_time



def remove_unwanted_chars(prompt):
  string_without_unwanted_chars = prompt.replace(u'\u00A0', ' ').replace(u'\u200b', '').replace("'", "\'").replace('"', '\"')

  return string_without_unwanted_chars
  
def construt_prompt(reply_str, question):

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

def upload_data_bq(question, answer, cdsid, tstamp ):

  # # Create the unique session ID by hashing the CDSID and concatenating with the timestamp
  # unique = cdsid + str(int(time.time()))
  # hash_object = hashlib.sha256(unique.encode('utf-8'))
  # sessionID = hash_object.hexdigest()

  # CARD_PAYLOAD['actions'][0]['data']['sessionID'] = sessionID
  # answer="Hello"
  # sessionID="1234567890"
  # question="How are you?"
  # exec_time=3.000989
  # tstamp="2023-10-27T11:10:46.788Z"
  # conversation_ID="12345678765432"
  # request_source="webex"
  answer=str(answer)
  answer = answer.replace('\n', '\\n') 

  query = f"""INSERT INTO `{PROJECT_ID}.chatgpt.{feedback_bq_table}` (cdsid, query)
VALUES ( '{cdsid}', '{question}')"""
  
  print(query)

  handle_proxies("UNSET")
  bigquery.Client(project = PROJECT_ID).query(query)

# Function to process incoming messages
def process_message(question):
  
  print(question)

  start_time = time.time()  

  sa_token, expiry_time = auth.fed_token(Client_id, Secret)
  
      
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

  # print(json.dumps(data, indent=4))
  json_data = json.dumps(data)

  logging.info(json_data)

  genapp_response = data['reply']['reply'] #Gen_App response

  # reply2 = [result["document"]["derivedStructData"]["extractive_answers"][0]["content"] for result in data["searchResults"]]   #Gen_App Extractive_Answers
  # reply_str = "\n\n".join(reply2) + "\n\n" + reply1

  genapp_response = re.sub(r'\[[^\]]*\]|\([^)]*\)', '', genapp_response)

  ##Create variations of questions using LLM

  qs_prompt=question_prompt(question)
  question_llm = LLM_MODEL.generate_content(qs_prompt)
  
  results = []

  try:
  # print(question_llm)
    question_response = json.loads(question_llm.text)
    question1, question2, question3=(json.dumps(question_response['answer 1']), question_response['answer 2'], question_response['answer 3'])
    print(question1, question2, question3)
    questions = [question1, question2]
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
        # extractive_answer = [result["document"]["derivedStructData"]["extractive_answers"][0]["content"] for result in data["searchResults"]] 
        # extractive_answer = genapp_reply + "\n\n".join(extractive_answer)
        results.append(genapp_reply)

  except (json.JSONDecodeError) as e:
    print("Error parsing JSON: {}".format(e))
    results = [genapp_response]

  prompt =  construt_prompt(str(results), question) ## 4. Construct prompt
  prompt = remove_unwanted_chars(prompt)

  print("This is the prompt:" + prompt) ##

  llm_response = LLM_MODEL.generate_content(   ## 5. generate response from LLM
      prompt,
      
    )

  print(llm_response)
  llm_data={}
  try:
      llm_data = json.loads(llm_response.text)
      print(llm_data['answer'])
      res = llm_data
  except (json.JSONDecodeError, Exception) as e:
      if isinstance(e, json.JSONDecodeError):
          print("Error parsing JSON: {}".format(e))
          print("Please rephrase the question or handle the response accordingly")
      else:
          print("Error in prompt:", e)
      res = {"answer": "NA", "id": "", "topic": ""}
  
  llm_answer=res['answer']

  if llm_answer != "NA":
    format_prompt=f"""Only using the below text as context, Create a well-structured and readable block of below text that explains a concept or process using clear and concise language. Pay attention to formatting, such as using bullet points, numbered lists, or headers, to improve the overall readability of the text.
    Context:-\n
    {llm_data['answer']}
    """

    format_response=LLM_MODEL.generate_content(format_prompt)

    print(format_response.candidates[0].content.parts[0].text)

  else:
    format_response = "I'm sorry, I'm not able to provide an answer at the moment. Could you please try rephrasing your question?"


  # print(format_prompt)
  # print(format_response)

  # print(reply[0])
  searchResults = []
  for item in data['searchResults']:
    searchResults.append(item['document']['derivedStructData']['link'])

  end_time = time.time()
  
  total_time = end_time - start_time
  
  return res, format_response, genapp_response, searchResults[:3], total_time

# Define a function to send messages to the Webex Teams API
def send_message(room_id, response_json, format_response, genapp_answer, suggested_list):
  # print(suggested_list)

  CARD_PAYLOAD['body'] = CARD_PAYLOAD['body'][:4]

  for item in suggested_list:
    print(item)
    title = item.split('/')[-1].replace('.pdf', '')
    # name = title.split(' — ')[0].split(' | ')[0].split(' — ')[0]
    name = title.split(' | ')[0].split(' — ')[0].split(' - ')[0]
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

    # format_data = json.loads(format_response.text)

    # print(format_response)
    # print(type(format_response))
  # print(str(format_response))
 
  CARD_PAYLOAD['body'][1]['text'] = format_response if response_json['answer'] == "NA" else str(format_response.candidates[0].content.parts[0].text)
    # CARD_PAYLOAD['body'][1]['text'] = response_json['answer']
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
  
def send_message_web(question, response_json, format_response, suggested_list):
  # print(suggested_list)

  CARD_PAYLOAD['body'] = CARD_PAYLOAD['body'][:4]

  links = {}

  for item in suggested_list:
      title = item.split('/')[-1].replace('.pdf', '')
      # name = title.split(' — ')[0].split(' | ')[0]
      # name = title.split(' — ')[0].split(' | ')[0]
      name = title.split(' | ')[0].split(' — ')[0].split(' - ')[0]
      print(name)
      
      if name in path:
          links[name] = f"<a href='{path[name]}' target='_blank'>{name}</a>"
 # Use the title as the key and the URL as the value
      else:
          links[name] = "https://docs.gcp.ford.com/docs/" 
      # print(links[title])

  res = {
    "question": question,
    "response" :  format_response if response_json['answer'] == "NA" else str(format_response.candidates[0].content.parts[0].text)
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
      logging.info(json_data)
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
  
  data = json.loads(request.data)  
  json_data = json.dumps(data)
  logging.info(json_data)


  sender_email=""
  cdsid=""

  if 'orgId' in data:
    print("The request is from Webex")

    validation, validation_msg = validate_request(request.get_data(), request.headers.get('X-Spark-Signature'))

    if validation == True : ##<----   *****
      request_source="web"
      data = json.loads(request.data)
      # print("Question:" + data['data']['text'])

      message_id = data['data']['id']
      room_id = data['data']['roomId']
      # print(message_id)

      conversation_ID = get_conversation_id(room_id)

      print(conversation_ID)

      CARD_PAYLOAD['actions'][0]['data']['conversationID'] = conversation_ID

      

      if data['resource'] == "messages" and data['event'] == "created":

        sa_token, expiry_time = auth.fed_token(Client_id, Secret)

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
        
        cdsid=sender_email

        unique = sender_email + str(int(time.time()))
        hash_object = hashlib.sha256(unique.encode('utf-8'))
        sessionID = hash_object.hexdigest()

        CARD_PAYLOAD['actions'][0]['data']['sessionID'] = sessionID
        
        #Add the question to conversation_history
        url = f"https://discoveryengine.googleapis.com/v1/projects/ford-4360b648e7193d62719765c7/locations/global/collections/default_collection/dataStores/astrobot_1697723843614/conversations/{conversation_ID}:converse"

        payload = json.dumps({
          "query": {
            "input": message_text
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

        # Process the incoming message
        response_json, format_response, genapp_answer, suggested_list, total_time = process_message(message_text)

        print(f"Total execution time: {total_time} seconds")

        upload_data_bq(message_text, format_response,  sender_email, data['data']['created']) # Upload question-answer data to bq with unique sessionID


        send_message(room_id, response_json, format_response, genapp_answer, suggested_list)
      elif data['resource'] == "attachmentActions" and data['event'] == "created": # If incoming request is user's feedback -> a new attachmentAction (feedback) is created
        # Process incoming feedback and upload to Bigquery using session ID
        get_followup(message_id, room_id, data['data']['created'])
    else:
      return "Authentication failed!"

  elif "question" in data:
    request_source="web"
    print("The request is from Web")

    sessionID=""

    tstamp = '2023-10-27T11:10:46.788Z'

    if data.get("follow-up") == False:

      sa_token, expiry_time = auth.fed_token(Client_id, Secret)

      unique = cdsid + str(int(time.time()))
      hash_object = hashlib.sha256(unique.encode('utf-8'))
      sessionID = hash_object.hexdigest()

      cdsid=data['cdsid']
      question=data['question']

      conversation_ID = get_conversation_id(cdsid)

      print(conversation_ID)

      #Add the question to conversation_history
      url = f"https://discoveryengine.googleapis.com/v1/projects/ford-4360b648e7193d62719765c7/locations/global/collections/default_collection/dataStores/astrobot_1697723843614/conversations/{conversation_ID}:converse"

      payload = json.dumps({
        "query": {
          "input": question
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

      
      response_json, format_response, genapp_answer, suggested_list, total_time = process_message(question)
      # upload_data_bq(question, format_response,  cdsid, sessionID, conversation_ID, request_source, total_time, tstamp) # Upload question-answer data to bq with unique sessionID


      return send_message_web(question, response_json, format_response, suggested_list)
  
    elif data.get("follow-up") == True:

      question=data['question']
      cdsid=data['cdsid']

      conversation_ID = get_conversation_id(cdsid)

      followup_response, total_time = get_followup_web(question,conversation_ID)
      # return send_message_web(question, response_json, format_response, suggested_list)

      # upload_data_bq(question, format_response,  cdsid, sessionID, conversation_ID, request_source, total_time, tstamp) # Upload question-answer data to bq with unique sessionID


      response_json={"answer":""}
      response_json['answer']="NA"
      suggested_list=""
      return send_message_web(question, response_json, followup_response, suggested_list)
   
  else:
    return "Authentication failed!"

  return "Message received"

if __name__ == '__main__':
  PORT = 6000
  app.run(debug=True, host="0.0.0.0", port=PORT)



