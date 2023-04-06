# How to create embedding

## Preprocess the document library


We plan to use document embeddings to fetch the most relevant part of parts of our document library and insert them into the prompt that we provide to GPT-3. We therefore need to break up the document library into "sections" of context, which can be searched and retrieved separately.

Sections should be large enough to contain enough information to answer a question; but small enough to fit one or several into the GPT-3 prompt. We find that approximately a paragraph of text is usually a good length, but you should experiment for your particular use case. Here, I have prepared a CSV file related to cloud run from GCP Docs and giving it as input. 

```Text
title,heading,content,tokens
GCP Cloud Run,Summary,"Cloud Run is a managed compute platform that lets you run containers directly on top of Google's scalable infrastructure. ",22
GCP Cloud Run,Deploying Code on Cloud Run,"You can deploy code written in any programming language on Cloud Run if you can build a container image from it. In fact, building container images is optional. If you're using Go, Node.js, Python, Java, .NET Core, or Ruby, you can use the source-based deployment option that builds the container for you, using the best practices for the language you're using. ",80
GCP Cloud Run,Building Full-Featured Applications,"Google has built Cloud Run to work well together with other services on Google Cloud, so you can build full-featured applications. ",27
GCP Cloud Run,Increasing Developer Productivity,"Cloud Run allows developers to spend their time writing their code, and very little time operating, configuring, and scaling their Cloud Run service. You don't have to create a cluster or manage infrastructure in order to be productive with Cloud Run. ",49
GCP Cloud Run,Services and jobs: two ways to run your code ,"On Cloud Run, your code can either run continuously as a service or as a job. Both services and jobs run in the same environment and can use the same integrations with other services on Google Cloud. ",42
```

## Create Embedding Vector

We preprocess the document sections by creating an embedding vector for each section. An embedding is a vector of numbers that helps us understand how semantically similar or different the texts are. The closer two embeddings are to each other, the more similar are their contents. See the [documentation on OpenAI embeddings](https://platform.openai.com/docs/guides/embeddings) for more information.

This indexing stage can be executed offline and only runs once to precompute the indexes for the dataset so that each piece of content can be retrieved later. Since this is a small example, we will store and search the embeddings locally. If you have a larger dataset, consider using a vector search engine like Pinecone, Weaviate or Qdrant to power the search.

We have split our document library into sections, and encoded them by creating embedding vectors that represent each chunk. These embeddings will be used to answer our users' questions. These embeddings are strored as CSV file in the location : "./output/document_embedding.csv" .

 