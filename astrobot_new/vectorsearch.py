import vertexai
from langchain_community.vectorstores import MatchingEngine
from google.cloud.aiplatform.matching_engine._protos import match_service_pb2
from google.cloud.aiplatform.matching_engine._protos import match_service_pb2_grpc
import grpc
import os
from vertexai.language_models import TextEmbeddingModel, TextGenerationModel



EMBEDDING_MODEL = TextEmbeddingModel.from_pretrained("textembedding-gecko@001")
DEPLOYED_INDEX_SERVER_IP="10.25.4.5"
PROJECT_ID = "ford-4360b648e7193d62719765c7"
PROJECT_ID_VAI = "ford-071510988cc8f3cc7b39d2d8"

query="modern art in Europe"

def handle_proxies(cmd):
  if cmd == "UNSET":
    # Unset proxies
    os.environ['http_proxy']=''
    os.environ['https_proxy']=''
  else:
    # Set proxies
    os.environ['http_proxy']='http://internet.ford.com:83'
    os.environ['https_proxy']='http://internet.ford.com:83'

def get_embedding(question):

  handle_proxies("UNSET")
  vertexai.init(project = PROJECT_ID, location = "us-central1")

  handle_proxies("SET")
  emb_results = EMBEDDING_MODEL.get_embeddings([question])
  result = []
  for embedding in emb_results:
    result = embedding.values

  return result


test_embeddings = get_embedding(query)

print(test_embeddings)

channel = grpc.insecure_channel("{}:10000".format(DEPLOYED_INDEX_SERVER_IP)) # Make GRPC request to Machine engine index
stub = match_service_pb2_grpc.MatchServiceStub(channel)


request_ = match_service_pb2.MatchRequest()
request_.deployed_index_id = "astrobot2202241300dp"


for i in test_embeddings:
    request_.float_val.append(i) 
  
response = stub.Match(request_) 

print(response)








