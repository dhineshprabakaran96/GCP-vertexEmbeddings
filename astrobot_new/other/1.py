from typing import Tuple
import os
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import (
    OpenAITextCompletion,
    OpenAITextEmbedding,
)
from dotenv import load_dotenv
from semantic_kernel.connectors.memory.weaviate import weaviate_memory_store
from dotenv import load_dotenv

load_dotenv(verbose=True, override=True)

# Using Docker
config = weaviate_memory_store.WeaviateConfig(url="http://localhost:8080")

store = weaviate_memory_store.WeaviateMemoryStore(config=config)
store.client.schema.delete_all()

kernel = sk.Kernel()

api_key, org_id = sk.openai_settings_from_dot_env()

kernel.add_text_completion_service(
    "dv", OpenAITextCompletion("text-davinci-003", api_key, org_id)
)
kernel.add_text_embedding_generation_service(
    "ada", OpenAITextEmbedding("text-embedding-ada-002", api_key, org_id)
)

kernel.register_memory_store(memory_store=store)
kernel.import_skill(sk.core_skills.TextMemorySkill())

COLLECTION = "AboutMe"

#Function for persisting a memory to Weaviate
import uuid

async def populate_memory(kernel: sk.Kernel) -> None:
    # Add some documents to the semantic memory
    await kernel.memory.save_information_async(COLLECTION, 
                                               id = str(uuid.uuid4()), 
                                               text = 'When I turned 5 my parents gifted me goldfish for my birthday')
    
    await kernel.memory.save_information_async(COLLECTION,
                                              id = str(uuid.uuid4()),
                                              text = 'I love datascience')
    
    await kernel.memory.save_information_async(COLLECTION,
                                              id = str(uuid.uuid4()),
                                              text = 'I have a black nissan sentra')
    
    await kernel.memory.save_information_async(COLLECTION,
                                              id = str(uuid.uuid4()),
                                              text = 'my favourite food is popcorn')
    
    await kernel.memory.save_information_async(COLLECTION,
                                              id = str(uuid.uuid4()),
                                              text = 'I like to take long walks.')
    print("Sucessfully populated memories!")


    await populate_memory(kernel)


#Conduct semantic search

    result = await kernel.memory.search_async(COLLECTION, 'Do I have a pet?')
    print(f"Retreived document: {result[0].text}")

    result2 = await kernel.memory.search_async(COLLECTION, 'passion', limit=3)

    for res in result2: print(f"{res.text} - Relevance: {res.relevance:.3f}")

async def setup_RAG(kernel: sk.Kernel) -> Tuple[sk.SKFunctionBase, sk.SKContext]:
    sk_prompt = """
    You are a friendly and talkative AI.
    
    Answer to the user question: {{$user_input}} 
    
    You can, but don't have to, use relevant information provided here: {{$retreived_context}} 
    
    If you are not sure of the answer say "I am not sure."
    """.strip()

    rag_func = kernel.create_semantic_function(sk_prompt, max_tokens=200, temperature=0.8)

    context = kernel.create_new_context()

    #Need chat history now added to kernel context 
    context["chat_history"] = ""
    context["retreived_context"] = ""

    return rag_func, context


async def RAG(kernel: sk.Kernel, rag_func: sk.SKFunctionBase, context: sk.SKContext) -> bool:
    try:
        user_input = input("User:> ")
        context["user_input"] = user_input
    except KeyboardInterrupt:
        print("\n\nExiting chat...")
        return False
    except EOFError:
        print("\n\nExiting chat...")
        return False

    if user_input == "exit":
        print("\n\nExiting chat...")
        return False

    context["retreived_context"] = ''
    
    #Retrieve
    result = await kernel.memory.search_async(COLLECTION,context["user_input"], limit=5, min_relevance_score=0.5)
    
    for res in result:
        context["retreived_context"] += (res.text + '. \n')
    
    #Then generate
    answer = await kernel.run_async(rag_func, input_vars=context.variables)
    
    context["chat_history"] += f"\nUser:> {user_input}\nChatBot:> {answer}\n"

    print(f"\n\u001b[34mChatBot:> {answer}\u001b[0m \n\n\033[1;32m Source: {context['retreived_context']}\u001b[0m \n")
    return True

    print("Setting up a RAG chat (with memory!)")
    rag_func, context = await setup_RAG(kernel)

    print("Begin chatting (type 'exit' to exit):\n")
    chatting = True
    while chatting:
        chatting = await RAG(kernel, rag_func, context)

