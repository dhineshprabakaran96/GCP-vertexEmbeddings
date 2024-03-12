import os
from google.cloud import bigquery
import time

PROJECT_ID = "ford-4360b648e7193d62719765c7"



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
