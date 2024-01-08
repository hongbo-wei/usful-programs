'''
Count how many words that input text has
'''

def word_count(text):
    words = text.split()
    # Count the total number of words
    total_count = len(words)
    return total_count

text = ""
print("Enter your text to count words (type 'q' on a new line to finish input): ")
while True:
    # Take user input
    line = input()
    
    # Check if the user wants to exit
    if line.strip() == 'q':
        break
    
    # Concatenate the input text, preserving new lines
    text += line + '\n'

result = word_count(text)

print(result)

