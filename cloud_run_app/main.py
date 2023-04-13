from flask import Flask, render_template, request
import numpy as np
import openai
import pandas as pd

openai.api_version = '2022-12-01'
openai.api_base = 'https://ito-openai-instance.openai.azure.com/' # Please add your endpoint here
openai.api_type = 'azure'
openai.api_key = '113a243053474a77a78d7fd79fc6ae39'  # Azure Key-1

COMPLETIONS_MODEL = "deployment-851fdef5eaf64d8191f5d5270cadda4d" # ext-davinci-003
EMBEDDING_MODEL = "deployment-d38e46e6d5924a478a5c744a409a48d4" # text-embedding-ada-002


def load_embeddings(filename):
  location = "./embedding/" + filename
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
      deployment_id=EMBEDDING_MODEL,
      input=text
    )
    return result["data"][0]["embedding"]

def vector_similarity(x, y):
    # Returns the similarity between two vectors.
    # Because OpenAI Embeddings are normalized to length 1, the cosine similarity is the same as the dot product.\
    return np.dot(np.array(x), np.array(y))

def order_document_sections_by_query_similarity(query, contexts):\
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


df = pd.read_csv('./input/results.csv')
df = df.set_index(["title", "heading"])

document_embeddings = load_embeddings("document_embedding.csv")


MAX_SECTION_LEN = 500
SEPARATOR = "\n* "
# ENCODING = "gpt2"  # encoding for text-davinci-003
# encoding = tiktoken.get_encoding(ENCODING)
# separator_len = len(tokenizer.encode(SEPARATOR))
separator_len = 3

def answer_query_with_context(query,df,document_embeddings,show_prompt):
    prompt = construct_prompt(
        query,
        document_embeddings,
        df
    )
    
    if show_prompt:
        print(prompt)

    response = openai.Completion.create(
                deployment_id=COMPLETIONS_MODEL,
                prompt=prompt,
                **COMPLETIONS_API_PARAMS
            )

    return response["choices"][0]["text"].strip(" \n")

COMPLETIONS_API_PARAMS = {
    "temperature": 0.0,
    "max_tokens": 300,
}

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    message = request.form['message']
    # do something with the form data
    response = answer_query_with_context(message, df, document_embeddings, False)

    return response

if __name__ == "__main__":
    PORT = 8080
    app.run(debug=True, host="0.0.0.0", port=PORT)
