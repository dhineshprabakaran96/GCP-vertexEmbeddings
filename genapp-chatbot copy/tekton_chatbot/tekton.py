import requests
import json
import logging
import auth
import os
import re
from path import path
from flask import jsonify



Client_id= os.environ["CLIENT_ID"]
Secret=    os.environ["TERCES"]
TEKTON_BOT_ACCESS_TOKEN = os.environ["TEKTON_BOT_ACCESS_TOKEN"]
INTEGRATION_ACCESS_TOKEN=os.environ["INTEGRATION_ACCESS_TOKEN"]

conversation_ids = {}

sa_token, expiry_time = auth.fed_token(Client_id, Secret)

url="https://discoveryengine.googleapis.com/v1alpha/projects/655678175973/locations/global/collections/default_collection/dataStores/tekton-chatbot-datastore_1707543336032/conversations/-:converse"

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

def get_conversation_id(room_id):
  sa_token, expiry_time = auth.fed_token(Client_id, Secret)

  if room_id in conversation_ids:
      return conversation_ids[room_id]
  else:
      # Create Conversation history
      url="https://discoveryengine.googleapis.com/v1/projects/ford-4360b648e7193d62719765c7/locations/global/collections/default_collection/dataStores/astrobot_1697723843614/conversations"
      url="https://discoveryengine.googleapis.com/v1alpha/projects/655678175973/locations/global/collections/default_collection/dataStores/tekton-chatbot-datastore_1707543336032/conversations/-:converse"

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

def conversation_history(message_text, conversation_ID):
  #Add the question to conversation_history
  # url = f"https://discoveryengine.googleapis.com/v1/projects/ford-4360b648e7193d62719765c7/locations/global/collections/default_collection/dataStores/astrobot_1697723843614/conversations/{conversation_ID}:converse"
  url=f"https://discoveryengine.googleapis.com/v1alpha/projects/655678175973/locations/global/collections/default_collection/dataStores/tekton-chatbot-datastore_1707543336032/conversations/{conversation_ID}:converse"

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
  return response   


def genapp_response(question):
  
  
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

  json_data = json.dumps(data)

  logging.info(json_data)

  genapp_response = data['reply']['reply'] #Gen_App response

  genapp_response = re.sub(r'\[[^\]]*\]|\([^)]*\)', '', genapp_response)
  
  return genapp_response

def question_variation(question_llm):
  results = []

  try:
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

        results.append(genapp_reply)

  except (json.JSONDecodeError) as e:
    print("Error parsing JSON: {}".format(e))
    results = [genapp_response]
  
  searchResults = []
  for item in data['searchResults']:
    searchResults.append(item['document']['derivedStructData']['link'])
  
  return results, searchResults


def send_message(room_id, message_id, response_json, format_response, genapp_answer, suggested_list):
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
                    "title": "Astronomer Doc | Home",
                    "url":"https://pages.github.ford.com/gcam/astronomer-docs/" ## replace this URL for suggestion
                }
            ],
            "horizontalAlignment": "Left",
            "spacing": "Small"
        })
 
  CARD_PAYLOAD['body'][1]['text'] = format_response if response_json == "NA" else str(format_response.candidates[0])
  
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
      ],
      "placeholder": "Feedback",
      "style": "expanded"
  })
  # CARD_PAYLOAD["body"].append({
  #     "type": "Input.Text",
  #     "id": "feedbackComment",
  #     "placeholder": "Type your Feedback"
  # })
  
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
      "Authorization": f"Bearer {TEKTON_BOT_ACCESS_TOKEN}",
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
  


def send_message_space(room_id, message_id, response_json, format_response, genapp_answer, suggested_list):
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
  
  CARD_PAYLOAD['body'][1]['text'] = format_response if response_json == "NA" else str(format_response.candidates[0])
  
  # CARD_PAYLOAD["body"].append({
  #     "type": "Container"
  # })
  # CARD_PAYLOAD["body"].append({
  #     "type": "TextBlock",
  #     "text": "Got a follow-up question ?",
  #     "horizontalAlignment": "Left",
  #     "spacing": "Large",
  #     "fontType": "Monospace",
  #     "size": "Small",
  #     "color": "Dark",
  #     "isSubtle": True,
  #     "separator": True
  # })
  
  # CARD_PAYLOAD["body"].append({
  #     "type": "Input.Text",
  #     "id": "followup",
  #     "placeholder": "Type your follow-up question"
  # })
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
  # CARD_PAYLOAD["body"].append({
  #     "type": "Input.Text",
  #     "id": "feedbackComment",
  #     "placeholder": "Type your Feedback"
  # })

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
          links[name] = "https://docs.gcp.ford.com/docs/" 
      # print(links[title])

  res = {
    "question": question,
    "response" : format_response if response_json == "NA" else str(format_response.candidates[0])
,
    "links": list(links.values())   # Append the links to the res dictionary
  }

  return jsonify(res)

