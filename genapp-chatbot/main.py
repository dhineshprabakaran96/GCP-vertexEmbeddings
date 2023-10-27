from google.cloud import bigquery
from flask import Flask, request, jsonify
from google.cloud import logging
import logging 
import sys
import requests
import json
import hashlib
import hmac
import os

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

app = Flask(__name__)

BOT_ACCESS_TOKEN = os.environ["BOT_ACCESS_TOKEN"]
bot_email = "bmc-genapp@webex.bot"

PROJECT_ID = "ford-4360b648e7193d62719765c7"

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


# Function to process incoming messages
def process_message(question):

  # url = "https://discoveryengine.googleapis.com/v1alpha/projects/655678175973/locations/global/collections/default_collection/dataStores/top22bmcpdf_1696858258919/conversations/-:converse"
  url = "https://discoveryengine.googleapis.com/v1alpha/projects/655678175973/locations/global/collections/default_collection/dataStores/astrobot_1697723843614/conversations/-:converse"
  payload = json.dumps({
    "query": {
      "input": question
    },
    "summarySpec": {
      "summaryResultCount": 3,
      "ignoreAdversarialQuery": True,
      "includeCitations": True
    }
  })
  headers = {
    'Authorization': 'Bearer ' + os.environ["GCLOUD_ACCESS_TOKEN"],
    'Content-Type': 'application/json'
  }
  handle_proxies("SET")
  response = requests.request("POST", url, headers=headers, data=payload)

  data = json.loads(response.text)

  return data['reply']['reply']

# Define a function to send messages to the Webex Teams API
def send_message(room_id, response_text):

  CARD_PAYLOAD['body'][1]['text'] = response_text
  
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

  if validation == True : ##<----   *****

    data = json.loads(request.data)
    # logging.info(json.loads(request.data))

    message_id = data['data']['id']
    room_id = data['data']['roomId']

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
      response_text = process_message(message_text)

      send_message(room_id, response_text)
  
  else:
    return "Authentication failed!"

  return "Message received"

if __name__ == '__main__':
  PORT = 8085
  app.run(debug=True, host="0.0.0.0", port=PORT)

