import os
import sys

import openai
openai.api_key = open("OpenAIKey.txt").read()
openai.Model.list()

MODEL = "text-embedding-ada-002"

import qdrant_client as qc
import qdrant_client.http.models as qmodels

client = qc.QdrantClient(path="..\db")
METRIC = qmodels.Distance.DOT
DIMENSION = 1536

import uuid

if "-col" in sys.argv:
    COLLECTION_NAME = sys.argv[sys.argv.index("-col") + 1]
else:
    print("Please input the collection to be queried or created.")
    quit()

if os.path.isfile("indexes.txt"):
    db = open("indexes.txt")
    DATABASES = db.read()
    db.close()
else:
    db = open("indexes.txt", "w")
    DATABASES = ""
    db.close()

if COLLECTION_NAME in DATABASES and not "-index" in sys.argv:
    INDEXED = True
    SCORE = False
    if "-s" in sys.argv:
        SCORE = True

    ANSWERS = 1
    if "-ans" in sys.argv:
        ANSWERS = int(sys.argv[sys.argv.index("-ans") + 1])
elif "-q" in sys.argv:
    print("The selected database was not found. Please create a database before searching it.")
    quit()
else:
    INDEXED = False

    if "-if" in sys.argv:
        try:
            BOOK = sys.argv[sys.argv.index("-if")+1]
        except:
            print("Failed to provide a valid infile.")
            quit()
    elif not "-in" in sys.argv:
        print("Please input an infile as an argument: \"-if FILENAME.md\"")
        quit()

    EMBEDS = False
    if "-e" in sys.argv:
        try:
            e = open(BOOK + "Embeddings.txt")
            EMBEDS = True
            e.close()
        except:
            print("Failed to find an embeddings file. A new embeddings file will be generated.")

def prepMD(fileName):
    with open(fileName) as infile:
        mdFile = infile.read()
        mdFile = mdFile.replace("\n\n", "()")
        mdFile = mdFile.replace("\n", " ")
        mdFile = mdFile.replace("()", "\n\n")
        mdFile = mdFile.replace("## \n\n## ", "## ")
        while ("  " in mdFile):
            mdFile = mdFile.replace("  ", " ")
        return mdFile
    
def splitMD(preppedFile):
    mdFile = preppedFile.split("\n# ")
    for chapter in range(len(mdFile)):
        if chapter:
            mdFile[chapter] = "# " + mdFile[chapter]

        if "##" in mdFile[chapter]:
            mdFile[chapter] = mdFile[chapter].split("## ")
        else:
            mdFile[chapter] = mdFile[chapter].split("\n\n", 1)
            # mdFile[chapter] = mdFile[chapter].split("\n\n", 1)

        for sec in range(len(mdFile[chapter])):
            if sec and len(mdFile[chapter]) > 2:
                mdFile[chapter][sec] = "## " + mdFile[chapter][sec]
            while mdFile[chapter][sec][-1] == "\n":
                mdFile[chapter][sec] = mdFile[chapter][sec][:-1]

    return mdFile
    
def setHeaders(splitFile):
    ret = []
    cTitle = ""
    sTitle = ""
    text = ""
    for chapter in splitFile:
        for part in chapter:
            if part[:2] == "# ":
                cTitle = part[2:]
            else:
                if part[:3] == "## ":
                    temp = part[3:].split("\n\n", 1)
                    sTitle = temp[0]
                    text = temp[1]
                else:
                    sTitle = ""
                    text = part

                titleTuple = (cTitle, sTitle, text)
                ret.append(titleTuple)
    
    return ret

def embed_text(text):
    response = openai.Embedding.create(
        input = text,
        model = MODEL
    )
    embeddings = response['data'][0]['embedding']
    return embeddings

def embedBook(sections):
    open(BOOK + "embeddings.txt","w")
    ret = []
    for sec in sections:
        temp = embed_text(sec[2])
        ret.append((sec[0], sec[1], sec[2], temp))
        with open(BOOK + "embeddings.txt", 'a') as outfile:
            line = ""
            for i in temp:
                line += str(i)
                line += ", "
            line = line[:-2]
            line += "\n"
            outfile.write(line)
    with open(BOOK + "embeddings.txt") as infile:
        rev = infile.read()
        rev = rev[:-1]
    with open(BOOK + "embeddings.txt", "w") as outfile:
        outfile.write(rev)
    return ret

def getEmbeds(sections):
    ret = []
    with open(BOOK + "embeddings.txt") as infile:
        lines = infile.read()
        lines = lines.split("\n")
        for line in lines:
            sec = []
            line = line.split(", ")
            for val in line:
                sec.append(float(val))
            ret.append(sec)
    for i in range(len(sections)):
        ret[i] = (sections[i][0], sections[i][1], sections[i][2], ret[i])
    return ret

def create_index():
    client.recreate_collection(
    collection_name=COLLECTION_NAME,
    vectors_config = qmodels.VectorParams(
            size=DIMENSION,
            distance=METRIC,
        ),
    )
    return

def create_subsection_vector(subsection):
    id = str(uuid.uuid1().int)[:32]
    payload = {
        "Heading": subsection[0],
        "Subheading": subsection[1],
        "text": subsection[2]
    }
    return id, subsection[3], payload

def add_to_index(subsections):
    ids = []
    vectors = []
    payloads = []
    for sec in subsections:
        id, vector, payload = create_subsection_vector(sec)
        ids.append(id)
        vectors.append(vector)
        payloads.append(payload)
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=qmodels.Batch(
            ids = ids,
            vectors=vectors,
            payloads=payloads
        ),
    )
    return

def query_index(query):
    vector = embed_text(query)
    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=vector,
        with_payload=True
    )

    results = [
        (
            f"{res.payload['Heading']}\n{res.payload['Subheading']}",
            res.payload["text"],
            res.score,
        )
        for res in results
    ]

    return results

if INDEXED:
    if "-q" in sys.argv:
        try:
            question = sys.argv[sys.argv.index("-q") + 1:]
            question = ' '.join(question)
            if question and not question.isspace():
                answers = query_index(question)
                ans = min(ANSWERS, len(answers))
                for a in range(ans):
                    print(answers[a][0])
                    if SCORE:
                        print("Similarity Score: " + str(answers[a][2]))
                    print(answers[a][1])
            else:
                print("Please enter a query: -q \"QUERY\"")
        except:
            print("Please enter a query: -q \"QUERY\"")
    else:
        print("Please enter a query: -q \"QUERY\"")
else:
    print("Splitting book...")
    preppedBook = prepMD("../" + BOOK)
    splitBook = splitMD(preppedBook)
    chunks = setHeaders(splitBook)
    print("Book split.")
    if EMBEDS:
        print("Retrieving embeddings...")
        chunks = getEmbeds(chunks)
        print("Embeddings retrieved.")
    else:
        print("Generating embeddings...")
        chunks = embedBook(chunks)
        print("Embeddings generated.")
    print("Creating index...")
    create_index()
    print("Index created.")
    print("Adding to index...")
    add_to_index(chunks)
    print("Index filled.")
    db = open("indexes.txt")
    if not COLLECTION_NAME in db.read():
        db.close()
        db = open("indexes.txt", "a")
        db.write(COLLECTION_NAME)
        db.write("\n")
        print("Database added to records.")
    else:
        print("Database updated.")
    db.close()

"""print("Heading: " + chunks[0][0])
print("Subheading: " + chunks[0][1])
print("Text preview: " + chunks[0][2][:25])
print("Embeddings: " + str(chunks[0][3][:3]))"""