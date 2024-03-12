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
import os
import re
import auth
import time
import datetime
from datetime import datetime
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from langchain.chat_models import ChatVertexAI
from langchain.chains import SimpleSequentialChain
from validate_request import validate_request
from astronomer_chatbot import astronomer
from apigee_chatbot import apigee
from tekton_chatbot import tekton

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  


# sa_token, expiry_time = auth.fed_token(Client_id, Secret)

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

@app.route('/')
def index():
  res = {
    "response" : "Server is working fine!"
  }
  return jsonify(res)

@app.route('/cmsa/chatbot/astronomer', methods=['POST'])
def handle_webhook1():
  data=json.loads(request.data)  
  return astronomer.handle_webhook(data)

@app.route('/cmsa/chatbot/apigee', methods=['POST'])
def handle_webhook2():
  data=json.loads(request.data)  
  return apigee.handle_webhook(data)

@app.route('/cmsa/chatbot/tekton', methods=['POST'])
def handle_webhook3():
  data=json.loads(request.data)  
  return tekton.handle_webhook(data)


if __name__ == '__main__':
  PORT = 6000
  app.run(debug=True, host="0.0.0.0", port=PORT)


