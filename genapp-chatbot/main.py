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
bot_email = "chatBlueFord@webex.bot"

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

  url = "https://discoveryengine.googleapis.com/v1alpha/projects/655678175973/locations/global/collections/default_collection/dataStores/top22bmcpdf_1696858258919/conversations/-:converse"

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

  reply = data['reply']['reply']

  searchResults = []
  for item in data['searchResults']:
    searchResults.append(item['document']['derivedStructData']['link'].split('/')[-1].replace('.pdf', ''))
  
  # print(searchResults)
  return reply, searchResults[:3]

# Define a function to send messages to the Webex Teams API
def send_message(room_id, response_text, suggested_list):
  # print(response_json)

  CARD_PAYLOAD['body'] = CARD_PAYLOAD['body'][:4]

  suggested_id_list = "('" + "', '".join(suggested_list) + "')"
  bq_query = f"SELECT kba_id,article_title FROM `{PROJECT_ID}.chatgpt.bmc-kba-data-prod` where kba_id IN {suggested_id_list}"  # For getting suggestions
  bq_client = bigquery.Client(project = PROJECT_ID)
  rows = bq_client.query(bq_query).result().to_dataframe().values.tolist()  #list
  for item in rows:
    CARD_PAYLOAD["body"].append({
          "type": "ActionSet",
          "actions": [
              {
                  "type": "Action.OpenUrl",
                  "title": item[1],
                  "url": "https://ford-smartit.onbmc.com/smartit/app/#/knowledge/" + item[0]
              }
          ],
          "horizontalAlignment": "Left",
          "spacing": "Small"
      })
  # print(response_text)
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

@app.route('/webhook', methods=['POST'])
def handle_webhook():

  validation, validation_msg = validate_request(request.get_data(), request.headers.get('X-Spark-Signature'))
  # print(validation_msg)

  if validation == True : ##<----   *****

    data = json.loads(request.data)
    # print(str(data))

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
      response_text, suggested_list = process_message(message_text)

      send_message(room_id, response_text, suggested_list)
  
  else:
    return "Authentication failed!"

  return "Message received"

if __name__ == '__main__':
  PORT = 8085
  app.run(debug=True, host="0.0.0.0", port=PORT)




# gcloud auth application-default login    # If running in local

# export BOT_ACCESS_TOKEN=<PASTE BOT ACCESS TOKEN>
# export webhook_secret='<SECRET>'
# export ORG_ID=<CISCO ORG ID>
# export GCLOUD_ACCESS_TOKEN=<gcloud auth print-access-token>


