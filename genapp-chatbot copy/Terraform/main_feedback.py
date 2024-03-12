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


#ADFS Token credentials
Client_id= os.environ["CLIENT_ID"]
Secret=    os.environ["TERCES"]

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

app = Flask(__name__)

BOT_ACCESS_TOKEN = os.environ["BOT_ACCESS_TOKEN"]
bot_email = "bmc-genapp@webex.bot"

PROJECT_ID = "ford-4360b648e7193d62719765c7"

feedback_bq_table = "astro_GCP_bot_response_feedback"


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
            "title": "Submit Feedback",
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
  
def get_feedback(message_id, room_id):
  print(message_id)
  print(room_id)
  GET_URL = "https://webexapis.com/v1/attachment/actions/" + message_id

  headers = {
      "Authorization": f"Bearer {BOT_ACCESS_TOKEN}"
  }

  handle_proxies("SET")
  response = requests.get(GET_URL, headers=headers)

  json_data = response.json()

  print(json_data)

  # logging.info("feedback data")
  # logging.info(json_data)

  query = f"""UPDATE `{PROJECT_ID}.chatgpt.{feedback_bq_table}` 
  SET feedback='{json_data['inputs']['feedback']}', feedback_timestamp='{json_data['created']}', feedback_comment='{json_data['inputs']['feedbackComment']}'
  WHERE session_id='{json_data['inputs']['sessionID']}'"""

  logging.info(query) ## <----

  handle_proxies("UNSET")
  bigquery.Client(project = PROJECT_ID).query(query)

  # Send thank you message after feedback is captured
  headers = {
      "Authorization": f"Bearer {BOT_ACCESS_TOKEN}",
      "Content-Type": "application/json"
  }
  payload = {
      "roomId": room_id,
      "text": "Your feedback has been captured. Thank you!"
  }

  # Send the message to the Webex Teams API
  handle_proxies("SET")
  response = requests.post(
      "https://api.ciscospark.com/v1/messages",
      headers=headers,
      json=payload
  )

  

def upload_data_bq(question, answer, cdsid, tstamp, exec_time):

  # Create the unique session ID by hashing the CDSID and concatenating with the timestamp
  unique = cdsid + str(int(time.time()))
  hash_object = hashlib.sha256(unique.encode('utf-8'))
  sessionID = hash_object.hexdigest()
  print(sessionID)

  # response_time="{exec_time} seconds"
  # print(response_time)

  CARD_PAYLOAD['actions'][0]['data']['sessionID'] = sessionID


  query = f"""INSERT INTO `{PROJECT_ID}.chatgpt.{feedback_bq_table}` (session_id, cdsid, query, response, response_time, response_timestamp)
VALUES ('{sessionID}', '{cdsid}', '{question}', '{answer}', '{round(exec_time,3)} seconds', '{tstamp}')"""

  handle_proxies("UNSET")
  bigquery.Client(project = PROJECT_ID).query(query)


# Function to process incoming messages
def process_message(question):

  start_time = time.time()


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
    'Authorization': 'Bearer ' + auth.fed_token(Client_id, Secret),
    'Content-Type': 'application/json'
  }
  handle_proxies("SET")
  response = requests.request("POST", url, headers=headers, data=payload)

  data = json.loads(response.text)

  reply = data['reply']['reply']

  cleaned_reply = re.sub(r'\[[^\]]*\]|\([^)]*\)', '', reply)

  searchResults = []
  for item in data['searchResults']:
    searchResults.append(item['document']['derivedStructData']['link'])

  end_time = time.time()
  total_time = end_time - start_time
  
  # print(searchResults)
  return cleaned_reply, searchResults[:3], total_time

# Define a function to send messages to the Webex Teams API
def send_message(room_id, response_text, suggested_list):
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
  

  # print(response_text)
  CARD_PAYLOAD['body'][1]['text'] = response_text

   # ______________________ Capture Feedback __________________________
  CARD_PAYLOAD["body"].append({
      "type": "Container"
  })
  CARD_PAYLOAD["body"].append({
      "type": "TextBlock",
      "text": "Are you satisfied with the response?",
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
          {
              "title": "😑 Need Improvement",
              "value": "improve"
          }
      ],
      "placeholder": "Feedback",
      "style": "expanded"
  })
  CARD_PAYLOAD["body"].append({
      "type": "Input.Text",
      "id": "feedbackComment",
      "placeholder": "Type your Feedback"
  })
  
  # Set up the API request headers and payload
  headers = {
      "Authorization": f"Bearer {BOT_ACCESS_TOKEN}",
      "Content-Type": "application/json"
  }
  payload = {
      "roomId": room_id,
      "text": response_text,
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
      response_text, suggested_list, total_time = process_message(message_text)

      print(f"Total execution time: {total_time} seconds")

      upload_data_bq(message_text, response_text,  sender_email, data['data']['created'], total_time) # Upload question-answer data to bq with unique sessionID


      send_message(room_id, response_text, suggested_list)
    
    elif data['resource'] == "attachmentActions" and data['event'] == "created": # If incoming request is user's feedback -> a new attachmentAction (feedback) is created
      # Process incoming feedback and upload to Bigquery using session ID
      get_feedback(message_id, room_id)
    
    
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

