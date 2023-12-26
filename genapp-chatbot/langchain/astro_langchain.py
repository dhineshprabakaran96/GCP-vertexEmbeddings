#Handle both webex and web requests

import vertexai
from vertexai.language_models import TextGenerationModel
from langchain.memory import ConversationBufferWindowMemory
from langchain.memory import ConversationSummaryBufferMemory
from langchain.chains import SimpleSequentialChain
from langchain.chat_models import ChatVertexAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import SequentialChain
from langchain.chains import LLMChain
from langchain.chains import ConversationChain
from google.api_core.exceptions import GoogleAPIError
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


question="what is astronomer"

#ADFS Token credentials
Client_id= os.environ["CLIENT_ID"]
Secret=    os.environ["TERCES"]
# sa_token, expiry_time = auth.fed_token(Client_id, Secret)

conversation_ids = {}


BOT_ACCESS_TOKEN = os.environ["BOT_ACCESS_TOKEN"]
bot_email = "bmc-genapp@webex.bot"

PROJECT_ID = "ford-4360b648e7193d62719765c7"

llm_model=TextGenerationModel.from_pretrained("text-bison@001")
llm = ChatVertexAI(temperature=0.0, model=llm_model)

PARAMETERS = {
  "temperature": 0.1,
  "max_output_tokens": 1024,
  "top_p": 0.8,
  "top_k": 40
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

# Function to process incoming messages

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


genapp_response = data['reply']['reply'] #Gen_App response

# # print(genapp_response)

qs_prompt=question_prompt(question)
question_llm = llm_model.predict(qs_prompt, **PARAMETERS)
  
results = []

try:
# print(question_llm)
  question_response = json.loads(question_llm.text)
  question1, question2, question3=(json.dumps(question_response['answer 1']), question_response['answer 2'], question_response['answer 3'])
  # print(question1, question2, question3)
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



first_prompt= ChatPromptTemplate.from_template(f"Answer the query as truthfully as possible only using the provided context.""\n\n{question}" "Context:-\n" + str(results))


chain_one = LLMChain(llm=llm, prompt=first_prompt, 
                    output_key="answer"
                  )  

second_prompt=ChatPromptTemplate.from_template("""Only using the below text as context, Create a well-structured and readable block of below text that explains a concept or process using clear and concise language. Pay attention to formatting, such as using bullet points, numbered lists, or headers, to improve the overall readability of the text.
                                              Context:-\n""" "\n\n{answer}")
chain_two = LLMChain(llm=llm, prompt=second_prompt, 
                    output_key="format_response"
                  )

# overall_chain: input= Review 
# and output= English_Review,summary, followup_message
overall_chain = SequentialChain(
    chains=[chain_one, chain_two],
    input_variables=["question"],
    output_variables=["answer", "format_response"],
    verbose=True
)

results=overall_chain(question)
print(results['format_response'])





