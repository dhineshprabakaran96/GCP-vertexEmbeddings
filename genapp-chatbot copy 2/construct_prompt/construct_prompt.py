def construct_prompt(reply_str, question):

    #If the output contains a list of steps, where each step is separated by a period and a space, format the text so that each step is on a new line. format the text so that each step is on a new line. format the text so that each step is on a new line. If the answer field contains any step by step process, format it in new line
  header = """Answer the query as truthfully as possible only using the provided context. The answer should be in JSON format which contains answer (the answer to user\'s query), id (ID of the point in the context from where the information was taken), and topic (topic from context).  If the answer is not contained within the text below, return answer as \'NA\' and \'id\' and \'topic\' as most relevant in context. Provide necessary links to the supporting documents (if present in the context). " 

  Context:-\n
  """

  context = reply_str + '\n'

  examples = """input: What is Tensorflow?
  output: {\"answer\" : \"NA\", \"id\": \"\", \"topic\": \"\"}

  input: What is Sharepoint?
  output: {\"answer\" : \"NA\", \"id\": \"KBA00527160\", \"topic\": \"SharePoint Support Information\"}

  input: What is the Apigee API Publisher and how does it work?
  output: {\"answer\" : \"The Apigee API Publisher is a tool that allows API teams to deploy APIs to Apigee . It performs the following steps: 
           1. Runs the provided Swagger/OpenAPI v3 API specification through the Ford API Linter and 42Crunch Audit scan 
           2. Deploys an API proxy to the specified API gateway 
           3. Uploads the provided Swagger/OpenAPI v3 API specification to the API Catalog .\", \"id\": \"KBA00520474\", \"topic\": \"Webex in Mobile Support Information\"}

  """

  footer = f"input: {question}\noutput: \n"
  
  return header + context + examples + footer 