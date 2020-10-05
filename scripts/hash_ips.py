import csv
import hashlib

# Number of iterations of sha256.
ITERATIONS = 1000

# Recursive function to loop hashing.
def sha256_iterate(source, iterations):
    if type(source) == str:
        source = source.encode("utf8")
    
    if iterations < 1:
        raise ValueError("Iterations must be one (1) or above.")
    elif iterations == 1:
        return hashlib.sha256(source).hexdigest()
    else:
        source_hash = hashlib.sha256(source).digest()
        return sha256_iterate(source_hash, iterations-1)

# Run on file.
with open("../archive/alpha_supporters.csv", "r") as file:
    reader  = csv.reader(file)

    for row in reader:
        print(sha256_iterate(row[0], ITERATIONS))
