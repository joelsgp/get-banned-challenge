import csv
import hashlib

# Number of iterations of sha256.
ITERATIONS = 1000000

# Function to loop hashing.
# No longer recursive because of Python recursion depth limit of 1000.
def sha256_iterate(source, iterations):
    if type(source) == str:
        source = source.encode("utf8")
    
    if iterations < 1:
        raise ValueError("Iterations must be one (1) or above.")
    else:
        source_hash = hashlib.sha256(source).digest()
        iterations -= 1
        
        while iterations >= 1:
            source_hash = hashlib.sha256(source_hash).digest()

            iterations -= 1

    return hashlib.sha256(source_hash).hexdigest()

# Run on file.
with open("../archive/alpha_supporters.csv", "r") as file:
    reader  = csv.reader(file)

    for row in reader:
        print(sha256_iterate(row[0], ITERATIONS) + "<br>")
