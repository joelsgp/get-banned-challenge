# this program made by JMcB#7918 on discord or whatever

# Import some default modules.
# lmao so random holds up spork
import random
import functools
import os.path

discord_char_limit = 2000

# Check if the file to record which words have been tried exists.
# Decide which file to read from based on the result.
if os.path.isfile("untried_words.txt"):
    words_file_path = "untried_words.txt"  
else:
    words_file_path = "words.txt"

# Read the file and parse it into a Python list.
print("Reading and processing words file.")

with open(words_file_path, "r") as words_file:
    words_file_contents = words_file.read()
words_list = eval(words_file_contents)

original_list_length = len(words_list)
print("{} words loaded and processed.".format(len(words_list)))

# Function to find cumulative length of all strings in list.
def cum_length(target_list):
    return functools.reduce(lambda x,y: x+len(y)+1, target_list, 0)

# Declare a variable for the message words as an empty list.
message_words = []
# Keep adding words until you reach the discord char limit.
print("Generating message.")
while  cum_length(message_words) < discord_char_limit:
    word_index = random.randint(0, len(words_list)-1)
    message_words.append(words_list[word_index])
    del words_list[word_index]

# Message is now too long, remove one word from message.
words_list.append(message_words.pop())
# Combine words in list into one string.
message = " ".join(message_words)
print("Generated message with length {}.".format(len(message)))

# Here is your message!
print("Here is your message!\n")
print(message)

# SAVE a file containing words that have not been tried yet.
with open("untried_words.txt", "w") as untried_words_file:
    untried_words_file.write(str(words_list))
    
print("\nSaved {} words to progress record file.".format(len(words_list)))
print("That's {} words tried!".format(original_list_length-len(words_list)))
print("DM me if you found the word and got banned. Thanks for using.")

# The thought of finding the banned word fills you with determination.
    
input()
