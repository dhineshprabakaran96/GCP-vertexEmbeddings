import vertexai
from vertexai.language_models import TextEmbeddingModel, TextGenerationModel
from google.cloud.aiplatform.matching_engine._protos import match_service_pb2
from google.cloud.aiplatform.matching_engine._protos import match_service_pb2_grpc
import grpc
from google.cloud import bigquery
from flask import Flask, request, jsonify
from google.cloud import logging
import logging as log
import requests
import json
import hashlib
import hmac
import os
import time

app = Flask(__name__)

# Set up global variables
BOT_ACCESS_TOKEN = os.environ["BOT_ACCESS_TOKEN"]
bot_email = "chatBlueFord@webex.bot"

PROJECT_ID = "ford-4360b648e7193d62719765c7"
PROJECT_ID_VAI = "ford-071510988cc8f3cc7b39d2d8"

bmc_bq_data_table = "bmc-kba-data-prod"
feedback_bq_table = "bmc-feedback-data"

EMBEDDING_MODEL = TextEmbeddingModel.from_pretrained("textembedding-gecko@001")
LLM_MODEL = TextGenerationModel.from_pretrained("text-bison@001")

PARAMETERS = {
  "temperature": 0.1,
  "max_output_tokens": 1000,
  "top_p": 0.8,
  "top_k": 40
}

MAX_INPUT_TOKENS = 4000

# Webex Card boilerplate
CARD_PAYLOAD = {
    "type": "AdaptiveCard",
    "body": [
        {
            "type": "TextBlock",
            "text": "BMC Chatbot",
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

# Get Embeddings for input text
def get_embedding(question):

  handle_proxies("UNSET")
  vertexai.init(project = PROJECT_ID, location = "us-central1")

  handle_proxies("SET")
  emb_results = EMBEDDING_MODEL.get_embeddings([question])
  result = []
  for embedding in emb_results:
    result = embedding.values

  return result


# Message text are encrypted. So we need to make GET request by passing message ID to decrypt it
def get_message(message_id):

  GET_URL = "https://webexapis.com/v1/messages/" + message_id

  headers = {
      "Authorization": f"Bearer {BOT_ACCESS_TOKEN}"
  }

  handle_proxies("SET")
  response = requests.get(GET_URL, headers=headers)

  if response.status_code == 200:  # Request was successful
    json_data = response.json()
    return json_data['text']
  else:
    return 'Request failed with status code: ' + str(response.status_code)

# Get feedback details and upload it to bigquery using session ID
def get_feedback(message_id, room_id):
  GET_URL = "https://webexapis.com/v1/attachment/actions/" + message_id

  headers = {
      "Authorization": f"Bearer {BOT_ACCESS_TOKEN}"
  }

  handle_proxies("SET")
  response = requests.get(GET_URL, headers=headers)

  json_data = response.json()

  query = f"""UPDATE `{PROJECT_ID}.chatgpt.{feedback_bq_table}` 
SET feedback='{json_data['inputs']['feedback']}', feedback_timestamp='{json_data['created']}'
WHERE session_id='{json_data['inputs']['sessionID']}'"""

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


# Remove unwanted chars form prompt
def remove_unwanted_chars(prompt):
  string_without_unwanted_chars = prompt.replace(u'\u00A0', ' ').replace(u'\u200b', '').replace("'", "\'").replace('"', '\"')

  return string_without_unwanted_chars


# Construct Prompt for LLM
def construt_prompt(rows, question):

  header = """Answer the query as truthfully as possible only using the provided context. The answer should be in JSON format which contains answer (the answer to user\'s query), id (ID of the point in the context from where the information was taken), and topic (topic from context). If the answer is not contained within the text below, return answer as \'NA\' and \'id\' and \'topic\' as most relevant in context. Provide necessary links to the supporting documents (if present in the context).

Context:-\n
"""

  context = ""
  tokens_till_now = 0
  for row in rows:
    if tokens_till_now > MAX_INPUT_TOKENS:
      break
    context += f"*Topic: {row[2]}\nID: {row[1]}\n{row[0]}\n\n"
    tokens_till_now += row[3]

  examples = """input: What is Tensorflow?
output: {\"answer\" : \"NA\", \"id\": \"\", \"topic\": \"\"}

input: What is Sharepoint?
output: {\"answer\" : \"NA\", \"id\": \"KBA00527160\", \"topic\": \"SharePoint Support Information\"}

input: How to install webex in mobile?
output: {\"answer\" : \"Corporate Mobile:  Note: The Webex App should be installed by default on all Corporate and Intune-managed devices. If you need to re-install the app, follow the below steps:\\n 1. Open the Corporate App Store application in the mobile device.\\n 2. Enter \'Webex\' in the search bar.\\n 3. Click \'Search\'.\\n  4. Select \'Webex\' application.\\n 5. Click \'Install\'.   Personal Mobile:  Webex application can be downloaded from iPhone App store / Google Play store available in their device.\", \"id\": \"KBA00520474\", \"topic\": \"Webex in Mobile Support Information\"}

"""

  footer = f"input: {question}\noutput: \n"

  return header + context + examples + footer

# Upload user's question and answer to bigquery using unique session ID
def upload_data_bq(question, answer, cdsid, tstamp):

  # Create the unique session ID by hashing the CDSID and concatenating with the timestamp
  unique = cdsid + str(int(time.time()))
  hash_object = hashlib.sha256(unique.encode('utf-8'))
  sessionID = hash_object.hexdigest()

  CARD_PAYLOAD['actions'][0]['data']['sessionID'] = sessionID

  query = f"""INSERT INTO `{PROJECT_ID}.chatgpt.{feedback_bq_table}` (session_id, cdsid, query, response, response_timestamp)
VALUES ('{sessionID}', '{cdsid}', '{question}', '{answer}', '{tstamp}')"""

  handle_proxies("UNSET")
  bigquery.Client(project = PROJECT_ID).query(query)


# Function to get some suggestions , if not suggestions returned from LLM
def get_suggestions(res, id_list, id_distance):
  suggested_list = []
  # print(id_list)
  # print(id_distance)

  if len(res['topic']) == 0 and len(res['id']) == 0:
    print("need some suggestions...")

    for i in range(0, len(id_list)):
      if len(suggested_list) >= 3:
        break
      if id_distance[i] > 0.65:
        suggested_list.append(id_list[i])

  return suggested_list

# Function to process incoming messages
def process_message(question):

  if len(question) < 8:  # Input query should be at least 8 chars long
    return {"answer": "insufficient", "id": "", "topic": ""}
  
  test_embeddings = get_embedding(question) ## 1. Get embeddings for query (question)

  handle_proxies("UNSET")  # We need to set and unset proxies during runtime

  vertexai.init(project = PROJECT_ID_VAI, location = "us-central1")

  handle_proxies("SET")

  DEPLOYED_INDEX_SERVER_IP = os.environ["index_ip"]

  channel = grpc.insecure_channel("{}:10000".format(DEPLOYED_INDEX_SERVER_IP)) # Make GRPC request to Machine engine index
  stub = match_service_pb2_grpc.MatchServiceStub(channel)

  request_ = match_service_pb2.MatchRequest()
  request_.deployed_index_id = "bmc_kba_prod_endpoint_2"

  for i in test_embeddings:
    request_.float_val.append(i) 
  
  response = stub.Match(request_)  ## 2. Get nearest distance vectors from matching engine

  id_list = [] # list to store nearest IDs
  id_distance = []  # List to store distance parameters

  for i in response.neighbor:
    id_list.append(i.id)
    id_distance.append(i.distance)

  # print(id_list)
  # print(id_distance)

  suggested_id_list = "('" + "', '".join(id_list[:5]) + "')"

  handle_proxies("UNSET")

  bq_query = f"SELECT answer,kba_id,article_title,tokens FROM `{PROJECT_ID}.chatgpt.{bmc_bq_data_table}` where id IN {suggested_id_list}"  # 3. Make query to bq table with top ID
  # print(bq_query)
  
  bq_client = bigquery.Client(project = PROJECT_ID)
  rows = bq_client.query(bq_query).result().to_dataframe().values.tolist()  #list

  prompt =  construt_prompt(rows, question) ## 4. Construct prompt
  prompt = remove_unwanted_chars(prompt)

  handle_proxies("SET")

  llm_response = LLM_MODEL.predict(   ## 5. generate response from LLM
      prompt,
      **PARAMETERS
    )

  # The incoming response from LLM should be in json format - {"answer": "NA", "id": "", "topic": ""}
  try:
    res = eval(llm_response.text)

  except Exception as e:
    print("Error in prompt:", e)
    res = {"answer": "NA", "id": "", "topic": ""}

  suggested_list = get_suggestions(res, id_list, id_distance)
  # print(suggested_list)

  return res, suggested_list

# Define a function to send messages to the Webex Teams API
def send_message(room_id, response_json, suggested_list):

  CARD_PAYLOAD["body"] = CARD_PAYLOAD["body"][:2] # Clear card with previous data

  if response_json['answer'] == 'insufficient':
    # handle insufficient input
    CARD_PAYLOAD["body"][1]["text"] = "Insufficient input. Input should be at least 8 chars long. Please try again!"
  elif response_json['answer'] == 'NA' or response_json['answer'] == 'NA ':
    # handle answee = 'NA'
    CARD_PAYLOAD["body"][1]["text"] = "Could you please provide more details or rephrase the question to help me understand better?" 
    # If suggestions are provided
    if len(response_json['topic'])>0 and len(response_json['id'])>0:
      CARD_PAYLOAD["body"].append({
              "type": "TextBlock",
              "text": "However, I found some information which might be helpful: ",
              "horizontalAlignment": "Left",
              "wrap": True,
              "fontType": "Default",
              "size": "Default",
              "weight": "Default",
              "color": "Default"
          })
      CARD_PAYLOAD["body"].append({
              "type": "ActionSet",
              "actions": [
                  {
                      "type": "Action.OpenUrl",
                      "title": response_json['topic'],
                      "url": "https://ford-smartit.onbmc.com/smartit/app/#/knowledge/" + response_json['id']
                  }
              ],
              "horizontalAlignment": "Left",
              "spacing": "Small"
          })
    elif len(suggested_list) > 0:
      # If suggestions not provided - Handle additional suggestions
      CARD_PAYLOAD["body"].append({
              "type": "TextBlock",
              "text": "However, I found some information which might be helpful: ",
              "horizontalAlignment": "Left",
              "wrap": True,
              "fontType": "Default",
              "size": "Default",
              "weight": "Default",
              "color": "Default"
          })
      suggested_id_list = "('" + "', '".join(suggested_list) + "')"
      bq_query = f"SELECT kba_id,article_title FROM `{PROJECT_ID}.chatgpt.{bmc_bq_data_table}` where id IN {suggested_id_list}"  # For getting suggestions
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

  else:
    # Enriched response
    CARD_PAYLOAD["body"][1]["text"] = response_json['answer']
    if len(response_json['topic'])>0 and len(response_json['id'])>0:
      CARD_PAYLOAD["body"].append({
              "type": "TextBlock",
              "text": "For more information: ",
              "horizontalAlignment": "Left",
              "wrap": True,
              "fontType": "Default",
              "size": "Default",
              "weight": "Default",
              "color": "Default"
          })
      CARD_PAYLOAD["body"].append({
              "type": "ActionSet",
              "actions": [
                  {
                      "type": "Action.OpenUrl",
                      "title": response_json['topic'],
                      "url": "https://ford-smartit.onbmc.com/smartit/app/#/knowledge/" + response_json['id']
                  }
              ],
              "horizontalAlignment": "Left",
              "spacing": "Small"
          })

  # ______________________ Capture Feedback __________________________
  CARD_PAYLOAD["body"].append({
      "type": "Container"
  })
  CARD_PAYLOAD["body"].append({
      "type": "TextBlock",
      "text": "Are you satisfied with the repsonse?",
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

# *********** Handle incoming POST request on /webhook endpoint
@app.route('/webhook', methods=['POST'])
def handle_webhook():

  validation, validation_msg = validate_request(request.get_data(), request.headers.get('X-Spark-Signature'))  # Check incoming request - Validate
  # print(validation_msg)

  if validation == True : ##   <--***** Make != if testing from postman

    data = json.loads(request.data)

    message_id = data['data']['id']
    room_id = data['data']['roomId']

    if data['resource'] == "messages" and data['event'] == "created":  # If incoming request is user's query -> a new message event is created``
      
      sender_email = data['data']['personEmail']

      # Check if the message came from the bot, to avoid infinite loops
      if sender_email == bot_email:
          return "OK"

      # Process incoming request
      message_text = ""
      if 'text' in data['data'].keys():  # I used for postman testing. There won't be 'text' field under 'data' in incoming request from cisco.
        message_text = data['data']['text']
      else:
        message_text = get_message(message_id)

      response_json, suggested_list = process_message(message_text) # Returns LLM response and suggestion

      upload_data_bq(message_text, response_json['answer'], sender_email, data['data']['created']) # Upload question-answer data to bq with unique sessionID

      send_message(room_id, response_json, suggested_list) # Send LLM response to user 
    
    elif data['resource'] == "attachmentActions" and data['event'] == "created": # If incoming request is user's feedback -> a new attachmentAction (feedback) is created
      # Process incoming feedback and upload to Bigquery using session ID
      get_feedback(message_id, room_id)
  
  else:
    return "Authentication failed!"

  return "Message received"

if __name__ == '__main__':
  PORT = 8088
  app.run(debug=True, host="0.0.0.0", port=PORT)

