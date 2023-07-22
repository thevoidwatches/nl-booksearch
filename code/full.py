# Needed for command line argumetns 
import os
import sys

# Sets up OpenAI constants
import openai
openai.api_key = open("OpenAIKey.txt").read()
openai.Model.list()
MODEL = "text-embedding-ada-002"

# sets up QDrant constants
import qdrant_client as qc
import qdrant_client.http.models as qmodels
client = qc.QdrantClient(path="..\db")
METRIC = qmodels.Distance.DOT
DIMENSION = 1536
import uuid

# argument for naming the database/Qdrant collection to operate on.
# has no default, as it's required regardless of operation.
# if no database name is provided, throw and error and quit.
if "-col" in sys.argv:
    COLLECTION_NAME = sys.argv[sys.argv.index("-col") + 1]
else:
    print("Please input the collection to be queried or created.")
    quit()

# If there's an existing list of already-created databases, reads it into a variable. Otherwise, creates a blank new file.
if os.path.isfile("indexes.txt"):
    db = open("indexes.txt")
    DATABASES = db.read()
    db.close()
else:
    db = open("indexes.txt", "w")
    DATABASES = ""
    db.close()

if COLLECTION_NAME in DATABASES and "-q" in sys.argv:
    # If the chosen database exists and you're searching it, set QUERY to True to split between indexing and querying.
    QUERY = True

    # argument to display the similarity score of the matched passage in addition to the text itself - defaults to false.
    SCORE = False
    if "-s" in sys.argv:
        SCORE = True

    # argument to display multiple matching passages - defaults to 1.
    ANSWERS = 1
    if "-ans" in sys.argv:
        ANSWERS = int(sys.argv[sys.argv.index("-ans") + 1])
elif COLLECTION_NAME in DATABASES and "-index" in sys.argv:
    # If the database exists and you're indexing it, set INDEXED to False
    QUERY = False

    if "-if" in sys.argv:
        # Sets the infile - the book to be read.
        try:
            BOOK = sys.argv[sys.argv.index("-if")+1]
        except:
            # If there's an error while trying to read it, throw an error and quit.
            print("Failed to provide a valid infile.")
            quit()
    elif not "-in" in sys.argv:
        # If no infile is provided at all, throw an error and quit.
        print("Please input an infile as an argument: \"-if FILENAME.md\"")
        quit()

    # Argument for using an embeddings.txt file to avoid regenerating the embeddings each time the book is re-indexed.
    EMBEDS = False
    if "-e" in sys.argv and os.path.isfile(BOOK[:-3] + "Embeddings.txt"):
        EMBEDS = True
    elif "-e" in sys.argv:
        print("Failed to find an embeddings file. A new embeddings file will be generated.")
elif not COLLECTION_NAME in DATABASES and "-q" in sys.argv:
    # If the chosen database doesn't exist, and you're attempting to question it, throw an error and quit.
    print("The selected database was not found. Please create a database before searching it.")
    quit()
else:
    print("Please use the -q or -index arguments to operate on the chosen database.")
    quit()

# function for reading a markdown file and cleaning the generated text
def prepMD(fileName):
    with open(fileName) as infile:
        mdFile = infile.read()
        # turn single line breaks into spaces, while leaving double line breaks.
        mdFile = mdFile.replace("\n\n", "TEMPDOUBLELINEBREAK")
        mdFile = mdFile.replace("\n", " ")
        mdFile = mdFile.replace("TEMPDOUBLELINEBREAK", "\n\n")
        # remove blank headers
        mdFile = mdFile.replace("# \n\n#", "# ")
        # remove excess spaces
        while ("  " in mdFile):
            mdFile = mdFile.replace("  ", " ")
        return mdFile
    
# function for splitting a prepared markdown file into chapters with sections
# works on first and second-level markdown headers.
def splitMD(preppedFile):
    # splits the single file into chapters
    mdFile = preppedFile.split("\n\n# ")
    for chapter in range(len(mdFile)):
        # Because split() removes the delimiters, prepend the header mark to each chapter (other than the first, which keeps it, as it has no newline characters to mark it to be split)
        if chapter:
            mdFile[chapter] = "# " + mdFile[chapter]

        if "##" in mdFile[chapter]:
            # if there are any second-level headers in the file, splits on those to find subsections of the chapter.
            mdFile[chapter] = mdFile[chapter].split("## ")
        else:
            # if not, splits the header from the rest of the chapter.
            mdFile[chapter] = mdFile[chapter].split("\n\n", 1)
            # mdFile[chapter] = mdFile[chapter].split("\n\n", 1)

        for sec in range(len(mdFile[chapter])):
            if sec and len(mdFile[chapter]) > 2:
                # for each section in chapters that have multiple subsections, prepend the header mark.
                # this is untrue for the header of each chapter and for any chapters with only a single subsection.
                mdFile[chapter][sec] = "## " + mdFile[chapter][sec]
            # remove and excess newlines from the beginning or end of each header or subsection.
            while mdFile[chapter][sec][-1] == "\n":
                mdFile[chapter][sec] = mdFile[chapter][sec][:-1]
            while mdFile[chapter][sec][0] == "\n":
                mdFile[chapter][sec] = mdFile[chapter][sec][1:]

    return mdFile
    
# function to take the split book file (which should be a list of chapters which are lists of and subsections) and turn it into a list of chunks (each of which should be a tuple made up of the chapter title, subsection title if there is one, and text of the subsection)
def setHeaders(splitFile):
    ret = []
    cTitle = ""
    sTitle = ""
    text = ""
    for chapter in splitFile:
        for part in chapter:
            if part[:2] == "# ":
                # if the current section starts with a first-level header, sets the title of the chapter
                cTitle = part[2:]
            else:
                # otherwise it's a subsection within the chapter, and will be added as a tuple
                if part[:3] == "## ":
                    # if it starts with a second-level header, sets the current subsection title and the text
                    temp = part[3:].split("\n\n", 1)
                    sTitle = temp[0]
                    text = temp[1]
                else:
                    # otherwise, it's just the text, and the subsection has no title.
                    sTitle = ""
                    text = part

                titleTuple = (cTitle, sTitle, text)
                ret.append(titleTuple)
    
    return ret

# function to generate an OpenAI embedding from a string.
def embed_text(text):
    response = openai.Embedding.create(
        input = text,
        model = MODEL
    )
    embeddings = response['data'][0]['embedding']
    return embeddings

# fuction to take the chunks of a book (which should be a list of tuples, each consisting of a chapter title, subsection title if there is one, and text of the subsection) and append an OpenAI embedding to each. Also writes the embeddings to a text document, for later retrieval.
def embedBook(sections):
    # creates a blank embeddings file for the current book.
    temp = open(BOOK[:-3] + "Embeddings.txt","w")
    temp.close()
    embeds = ""
    ret = []
    for sec in sections:
        # gets the embedding for the chunk's text and makes a new tuple for the chunk, adding it to the return list
        temp = embed_text(sec[2])
        chunk = (sec[0], sec[1], sec[2], temp)
        ret.append(chunk)

        # makes a line to add to the embeddings file
        line = ""
        for i in temp:
            if line:
                # if line isn't empty, there are already values in the line, so add a comma before adding the next value
                line += ", "
            # then add the value
            line += str(i)
        if embeds:
            # if embeds isn't empty, there are already lines in the file, so add a newline before the next line.
            embeds += "\n"
        # then add the line.
        embeds += line
    with open(BOOK[:-3] + "Embeddings.txt") as outfile:
        # after writing all of the embeddings, create an embeddings file.
        outfile.write(embeds)
    return ret

# function for retrieving embeddings from an embeddings file. Takes a set of chunks as input.
def getEmbeds(sections):
    ret = []
    with open(BOOK[:-3] + "Embeddings.txt") as infile:
        # split the file by lines using split() instead of readlines() so as to avoid trailing newline characters
        lines = infile.read()
        lines = lines.split("\n")
        if len(lines) == len(sections):
            # Only runs if there are the same number of embeddings as chunks
            for i in range(len(lines)):
                # split the line by commas to get invididual values for the embeddings
                embeds = []
                line = lines[i].split(", ")
                for e in line:
                    # make sure to convert them to floats as they're read
                    embeds.append(float(e))
                # create the tuple for the chunk and add it to the return list
                temp = (sections[i][0], sections[i][1], sections[i][2], embeds)
                ret.append(temp)
            print("Embeddings retrieved.")
        else:
            # if there aren't the right number of embeddings, generate new ones instead.
            print("Stored embeddings do not match to generated subsections.")
            print("Generating new embeddings...")
            ret = embedBook(sections)
            print("Embeddings generated.")
    return ret

# function to create a blank database using Qdrant
def create_index():
    client.recreate_collection(
    collection_name=COLLECTION_NAME,
    vectors_config = qmodels.VectorParams(
            size=DIMENSION,
            distance=METRIC,
        ),
    )
    return

# function to create a vector that can be stored in a Qdrant database
def create_subsection_vector(subsection):
    id = str(uuid.uuid1().int)[:32]
    payload = {
        "Heading": subsection[0],
        "Subheading": subsection[1],
        "text": subsection[2]
    }
    return id, subsection[3], payload

# function to add all created vectors to the created Qdrant database.
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

# function to query the created database
def query_index(query):
    # gets embeddings of the query
    vector = embed_text(query)

    # gets the results from the database
    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=vector,
        with_payload=True
    )

    # returns a list of tuples, each consisting of chapter title and subsection title, chapter text, and similarity score, for the results.
    ret = []
    
    for res in results:
        temp = (
            res.payload['Heading'] + "\n" + res.payload['Subheading'],
            res.payload["text"],
            res.score
        )
        ret.append(temp)
    return ret

# MAIN BODY OF THE PROGRAM

if QUERY:
    # with QUERY as true, you're querying an existing database.
    try:
        # get the question, as all arguments after -q, and join them together into a single string.
        question = sys.argv[sys.argv.index("-q") + 1:]
        question = ' '.join(question)

        if question and not question.isspace():
            # if question isn't an empty string or just spaces, run query_index to get a list of answers
            answers = query_index(question)

            # print as many of them as chosen in the ANSWERS argument (which defaults to 1)
            ans = min(ANSWERS, len(answers))
            for a in range(ans):
                # prints the chapter title and subsection title, the similarity score (only if the SCORE argument is true), and the text of the subsection
                print(answers[a][0])
                if SCORE:
                    print("Similarity Score: " + str(answers[a][2]))
                print(answers[a][1])

        # errors for if something goes wrong or if the query was empty
        else:
            print("Please enter a query: -q \"QUERY\"")
    except:
        print("Something went wrong while processing the query.")
else:
    # with QUERY as false, you're creating or updating a database.
    # first you prepare the book and turn it into chunks
    print("Splitting book...")
    preppedBook = prepMD("../" + BOOK)
    splitBook = splitMD(preppedBook)
    chunks = setHeaders(splitBook)
    print("Book split.")
    # if there's an existing embeddings file, get them - otherwise, retrieve them.
    if EMBEDS:
        print("Retrieving embeddings...")
        chunks = getEmbeds(chunks)
        # the getEmbeds() function reports success itself, because it will call embedBooks if no embeddings file is found.
    else:
        print("Generating embeddings...")
        chunks = embedBook(chunks)
        print("Embeddings generated.")
    # then create an empty database and fill it.
    print("Creating index...")
    create_index()
    print("Index created.")
    print("Adding to index...")
    add_to_index(chunks)
    print("Index filled.")
    
    # finally, add the database's name to indexes.txt if it's not already there.
    db = open("indexes.txt")
    if not COLLECTION_NAME in db.read():
        db.close()
        db = open("indexes.txt", "a")
        if db.read():
            db.write("\n")
        db.write(COLLECTION_NAME)
        print("Database added to records.")
    else:
        print("Database updated.")
    db.close()
