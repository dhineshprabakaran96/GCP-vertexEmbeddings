import json
from dotenv import load_dotenv
import streamlit as st
import PyPDF2
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain_google_vertexai import VertexAIEmbeddings
from vertexai.language_models import TextEmbeddingModel

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
      
      # create embeddings
      model = TextEmbeddingModel.from_pretrained("textembedding-gecko@001")
      embeddings = model.get_embeddings(chunks)

      embedding_data = {
          "embeddings": [embedding.values for embedding in embeddings]
      }

      # convert embeddings to lists before storing in JSON
      for embedding in embedding_data["embeddings"]:
          embedding["values"] = embedding["values"].tolist()

      # write the embeddings to a JSON file
      with open('embeddings.json', 'w') as json_file:
          json.dump(embedding_data, json_file)

if __name__ == '__main__':
    main()
