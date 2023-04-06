# ITO-ChatGPT

## Find the most similar document embeddings to the question embedding

At the time of question-answering, to answer the user's query we compute the query embedding of the question and use it to find the most similar document sections. Since this is a small example, we store and search the embeddings locally. If you have a larger dataset, consider using a vector search engine like Pinecone, Weaviate or Qdrant to power the search.


## Add the most relevant document sections to the query prompt

Once we've calculated the most relevant pieces of context, we construct a prompt by simply prepending them to the supplied query. It is helpful to use a query separator to help the model distinguish between separate pieces of text.