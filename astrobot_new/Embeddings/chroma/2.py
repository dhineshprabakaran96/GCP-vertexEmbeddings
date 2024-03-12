from langchain_google_vertexai import VertexAIEmbeddings

embeddings = VertexAIEmbeddings()

print(embeddings)

text = "This is a test document."

query_result = embeddings.embed_query(text)

doc_result = embeddings.embed_documents([text])

print(doc_result)