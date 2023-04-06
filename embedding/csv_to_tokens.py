# This program will add tokens for each row in the input CSV file
# This wil be required to generate embeddings

import csv
from transformers import GPT2TokenizerFast

tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")

def print_as_csv(csvFile):
  location = '<path_to_input_csv_file>.csv'
  with open(location, 'w') as file:
    file.write("%s,%s,%s,%s\n"%(csvFile[0][0],csvFile[0][1],csvFile[0][2],csvFile[0][3]))
    for items in csvFile[1:]:
        file.write("%s,%s,%s,%d\n"%(items[0],items[1],items[2],items[3]))
  print("Output saved to ", location)
  
  
# opening the CSV file
with open('./input/crun.csv', mode ='r') as file:

  csvFile = list(csv.reader(file))
  csvFile[0].append("tokens")
  for topic in range(1, len(csvFile)):
    tokens = len(tokenizer.encode(csvFile[topic][2]))
    csvFile[topic][2] = '"' + csvFile[topic][2] + '"'
    csvFile[topic].append(tokens)
  print_as_csv(csvFile)

  # for items in csvFile[1]:
  #   print(type(items))
  