from langchain.vectorstores.weaviate import Weaviate
from langchain.llms import OpenAI
from langchain.chains import ChatVectorDBChain
import weaviate

auth_config = weaviate.AuthApiKey(api_key="RbZZuIxHnoxq3LpfCerCP4h4q5684PuskBEE")


client = weaviate.Client(
  url="https://ford-astronomer-astrobot-3tdrhgxk.weaviate.network",
  auth_client_secret=auth_config
)


vectorstore = Weaviate(client, "PodClip", "content")

MyOpenAI = OpenAI(temperature=0.2,
    openai_api_key="sk-key")

qa = ChatVectorDBChain.from_llm(MyOpenAI, vectorstore)

chat_history = []

print("Welcome to the Weaviate ChatVectorDBChain Demo!")
print("Please enter a question or dialogue to get started!")

while True:
    query = input("")
    result = qa({"question": query, "chat_history": chat_history})
    print(result["answer"])
    chat_history = [(query, result["answer"])]