def remove_unwanted_chars(prompt):
  string_without_unwanted_chars = prompt.replace(u'\u00A0', ' ').replace(u'\u200b', '').replace("'", "\'").replace('"', '\"')

  return string_without_unwanted_chars
  