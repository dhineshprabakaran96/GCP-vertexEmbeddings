def question_prompt(question):
  
  header = """Compare and contrast three different phrasings for the following inquiry, utilizing vocabulary that is distinct and creative in each instance. The output should be in JSON format which contains the three phrasings

  Context:-\n
  """

  context = question

  examples = """input: What is Tensorflow?
  output: {\"answer\" : \"NA\"}

  input: What is Sharepoint?
  output: {\"answer 1\" : \"NA\", \"answer 2\" : \"NA\", \"answer 3\" : \"NA\"}

  input: How can I request access to a GCP service that Ford doesn't currently support?


  output: {\"answer 1\": \"What is the protocol for acquiring authorization to utilize a GCP service that is not yet endorsed by Ford?\",

\"answer 2\": \"I am seeking guidance on the procedure for gaining admittance to a GCP service that is not currently sanctioned by Ford. Can you assist me?\",

\"answer 3\": \"Is there a way for me to obtain permission to utilize a GCP service that Ford currently does not endorse? If so, what would the appropriate steps be?\"}

  """

  footer = f"input: {question}\noutput: \n"

  return header + context + examples + footer
