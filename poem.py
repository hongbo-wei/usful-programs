import random

# Define some dictionaries for poem generation
nouns = {
    "nature": ["forest", "mountain", "ocean", "flower", "bird"],
    "emotions": ["joy", "sadness", "love", "anger", "fear"],
    "objects": ["house", "book", "clock", "mirror", "key"],
}

verbs = {
    "action": ["run", "dance", "sing", "fight", "build"],
    "experience": ["see", "hear", "smell", "taste", "touch"],
}

adjectives = {
    "positive": ["happy", "bright", "warm", "calm", "gentle"],
    "negative": ["sad", "dark", "cold", "rough", "fierce"],
}


def generate_poem(keywords):
  """
  Generates a poem based on a list of keywords.

  Args:
      keywords: A list of strings representing keywords for the poem.

  Returns:
      A string containing the generated poem.
  """
  # Initialize poem lines
  lines = []

  # Loop through desired number of lines (adjust as needed)
  for i in range(4):
    # Choose a random noun based on a keyword
    noun = random.choice(nouns[random.choice(keywords)])

    # Choose random verbs and adjectives
    verb = random.choice(verbs[random.choice(["action", "experience"])])
    adj1 = random.choice(adjectives[random.choice(["positive", "negative"])])
    adj2 = random.choice(adjectives[random.choice(["positive", "negative"])])

    # Structure the line with placeholders
    line = f"A {adj1} {noun} {verb}s the {adj2} air."

    # Capitalize the first word for proper formatting
    lines.append(line.capitalize())

  # Join the lines with line breaks and return the poem
  return "\n".join(lines)


# Get keywords from user
keywords = input("Enter keywords (comma separated): ").lower().split(",")

# Generate and print the poem
poem = generate_poem(keywords)
print(poem)
