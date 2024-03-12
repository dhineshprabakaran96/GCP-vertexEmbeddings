from dotenv import load_dotenv
import streamlit as st
import PyPDF2
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
# from langchain.embeddings.openai import OpenAIEmbeddings
from langchain_google_vertexai import VertexAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain
# from langchain.llms import OpenAI
from langchain_google_vertexai import VertexAI
from langchain.callbacks import get_openai_callback
from vertexai.language_models import TextGenerationModel
from vertexai.language_models import TextEmbeddingModel
from google.cloud import bigquery


project_id="ford-4360b648e7193d62719765c7"
client = bigquery.Client(project=project_id)
dataset_id = 'chatgpt'
table_id = 'astrobot-new-vectorSearch-new-dp'

table_ref = client.dataset(dataset_id).table(table_id)
table = client.get_table(table_ref)



def main():
    load_dotenv()
    st.set_page_config(page_title="Ask your PDF")
    st.header("Ask your PDF 💬")
    
    # upload file
    pdf = st.file_uploader("Upload your PDF", type="pdf")
    
    # extract the text
    if pdf is not None:
      pdf_reader = PdfReader(pdf)
      text = ""
      for page in pdf_reader.pages:
        text += page.extract_text()
        
      # split into chunks
      text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
      )
      chunks = text_splitter.split_text(text)
      print(type(chunks))
      print(len(chunks))
      
      # create embeddings
      model = TextEmbeddingModel.from_pretrained("textembedding-gecko@001")
      embeddings = model.get_embeddings(chunks)
      # for embedding in embeddings:
      #     vector = embedding.values
      #     print(vector)
      #     print(f"Length of Embedding Vector: {len(vector)}")
      # return vector
      
      modified_vectors = [] 
      for i, embedding in enumerate(embeddings):
        vector = embedding.values
        modified_vector = '{{"id": "{}", "embedding": {}}}'.format(i+1, vector)  # Modify the format of the vector with the index of the chunk
        modified_vectors.append(modified_vector)  # Add the modified vector to the new list
        print(modified_vector)
        # print(f"Length of Embedding Vector: {len(vector)}")
      
      # return modified_vectors
      
      rows_to_insert = []
      for i, chunk in enumerate(chunks):
        row = {"id": i + 1, "chunk": chunk}
        rows_to_insert.append(row)

    # Insert the rows into the table, specifying the schema
      errors = client.insert_rows(table, rows_to_insert, selected_fields=table.schema)

      if errors:
          print(f'Errors occurred: {errors}')
      else:
          print('Chunks inserted into the existing BigQuery table successfully')

if __name__ == '__main__':
    main()