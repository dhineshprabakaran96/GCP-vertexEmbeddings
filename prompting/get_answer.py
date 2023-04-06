import os
import numpy as np
import openai
import pandas as pd
import tiktoken

openai.api_key = os.getenv("OPENAI_API_KEY")

COMPLETIONS_MODEL = "text-davinci-003"
EMBEDDING_MODEL = "text-embedding-ada-002"


def load_embeddings(filename):
  location = "./output/" + filename
  df = pd.read_csv(location, header=0).values.tolist()
  emb = {}
  for items in df:
    temp = []
    for i in range(2, len(items)):
      temp.append(items[i])
    emb[(items[0], items[1])] = temp

  return emb

def get_embedding(text):
    result = openai.Embedding.create(
      model=EMBEDDING_MODEL,
      input=text
    )
    return result["data"][0]["embedding"]

def vector_similarity(x, y):
    # Returns the similarity between two vectors.
    # Because OpenAI Embeddings are normalized to length 1, the cosine similarity is the same as the dot product.
    return np.dot(np.array(x), np.array(y))

def order_document_sections_by_query_similarity(query, contexts):
    # Find the query embedding for the supplied query, and compare it against all of the pre-calculated document embeddings
    # to find the most relevant sections. 
    # Return the list of document sections, sorted by relevance in descending order.

    query_embedding = get_embedding(query)
    
    document_similarities = sorted([
        (vector_similarity(query_embedding, doc_embedding), doc_index) for doc_index, doc_embedding in contexts.items()
    ], reverse=True)
    
    return document_similarities

def construct_prompt(question, context_embeddings, df):
    # Fetch relevant 

    most_relevant_document_sections = order_document_sections_by_query_similarity(question, context_embeddings)
    
    chosen_sections = []
    chosen_sections_len = 0
    chosen_sections_indexes = []
     
    for _, section_index in most_relevant_document_sections:
        # Add contexts until we run out of space.        
        document_section = df.loc[section_index]
        
        chosen_sections_len += document_section.tokens + separator_len
        if chosen_sections_len > MAX_SECTION_LEN:
            break
            
        chosen_sections.append(SEPARATOR + document_section.content.replace("\n", " "))
        chosen_sections_indexes.append(str(section_index))
            
    # Useful diagnostic information
    print(f"Selected {len(chosen_sections)} document sections:")
    print("\n".join(chosen_sections_indexes))
    
    header = """Answer the question as truthfully as possible using the provided context, and if the answer is not contained within the text below, say "I don't know."\n\nContext:\n"""
    
    return header + "".join(chosen_sections) + "\n\n Q: " + question + "\n A:"


df = pd.read_csv('./input/cloudrun.csv')
df = df.set_index(["title", "heading"])

document_embeddings = load_embeddings("document_embedding.csv")


MAX_SECTION_LEN = 500
SEPARATOR = "\n* "
ENCODING = "gpt2"  # encoding for text-davinci-003

encoding = tiktoken.get_encoding(ENCODING)
separator_len = len(encoding.encode(SEPARATOR))

def answer_query_with_context(query,df,document_embeddings,show_prompt):
    prompt = construct_prompt(
        query,
        document_embeddings,
        df
    )
    
    if show_prompt:
        print(prompt)

    response = openai.Completion.create(
                prompt=prompt,
                **COMPLETIONS_API_PARAMS
            )

    return response["choices"][0]["text"].strip(" \n")

COMPLETIONS_API_PARAMS = {
    # We use temperature of 0.0 because it gives the most predictable, factual answer.
    "temperature": 0.0,
    "max_tokens": 300,
    "model": COMPLETIONS_MODEL,
}

query = input("Type your query as a question : ")

print(answer_query_with_context(query, df, document_embeddings, False))

