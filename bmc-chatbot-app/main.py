import requests
import os
import json
from google.cloud import storage
from flask import Flask, request, jsonify

app = Flask(__name__)

# Define the URLs for token generation and data access
TOKEN_URL = 'https://ford-restapi.onbmc.com/api/jwt/login'
DATA_URL = """https://ford-restapi.onbmc.com/api/arsys/v1/entry/RKM:HowToTemplate_Manageable_Join?q=('InternalUse'="No")"""

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

# Function to get access token
def print_access_token():
  username = os.environ['username']
  password = os.environ['password']
  access_token = ""
  payload=f'username={username}&password={password}'
  headers = {
    'Content-Type': 'application/x-www-form-urlencoded'
  }
  
  handle_proxies("SET")
  response = requests.request("POST", TOKEN_URL, headers=headers, data=payload)
  if response.status_code == 200:
    access_token = response.text
  
  return access_token, response.status_code

# Function to get BMC data
def get_bmc_data(access_token):
  payload={}
  headers = {
    'Authorization': f'AR-JWT {access_token}'
  }

  handle_proxies("SET")
  response = requests.request("GET", DATA_URL, headers=headers, data=payload)
  return response.json(), response.status_code

# Function to store the response.json in GCS bucket
def store_bmc_data_gcs(data):
  bucket_name = 'bmc-chatbot-bucket'
  blob_name = 'response.json'
  handle_proxies("UNSET")
  client = storage.Client()
  bucket = client.get_bucket(bucket_name)
  blob = bucket.blob(blob_name)
  blob.upload_from_string(json.dumps(data))
  return blob.public_url


# Handle incoming POST request
@app.route('/webhook', methods=['POST'])
def handle_webhook():
  gcs_location = ""
  access_token, status_code = print_access_token()

  if status_code == 200:
    data, status_code = get_bmc_data(access_token)
    print("Data retrieved from BMC with statuscode", status_code)
    if status_code == 200:
      gcs_location = store_bmc_data_gcs(data)
  else:
    print("Some error with statuscode ", status_code)
    return "Some error with statuscode "+ status_code

  return "Data uploaded to " + gcs_location

if __name__ == '__main__':
  PORT = 8008
  app.run(debug=True, host="0.0.0.0", port=PORT)