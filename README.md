# Natural Language Booksearch

This program is designed to break down academic and other educational books into indexable databases, which can then be searched using queries written in natural language. It currently works only on books in markdown format (.md), and returns the most relevant subsection of a book as the answer to a query.

## How to Use

As a prerequisite to using this program, you **must** include a .txt file in the /code folder title OpenAIKey.txt (case-sensitive). This file must contain an API key for OpenAI (which can be generated [here](https://platform.openai.com/account/api-keys)) and otherwise be blank.

To use, first place a book, in markdown format, in the main folder. Then double-click the General Search shortcut, which will open a command prompt window, which will ask you to choose between querying an existing database and creating or updating a database.

### Creating or Updating a Database

Enter a lowercase 'c' to choose the option to create or update an existing database. The window will then ask you what book you wish to index - enter the full filename of the book, including the file suffix.

After you enter the book's name, it will ask you to name the database. If you are updating an existing database, it is important that you input the exact same name, as database names are case-sensitive. As such, be sure to use a memorable name when creating a new database.

The program will then allow you to exit, or to begin querying databases.

### Querying a Database.

Enter a lowercase 'q' to query a database. The program will first ask you which of the stored databases you wish to saerch - type in the name of the database chosen when creating it. If no matching database is found, it will allow you to choose again, or simply close the program.

After succesfully finding an extant database, the program will allow you to enter your question. Type it in natural language, e.g. "What is the main topic of this book?" The program will process your query and return the most appropriate subsection of the book. After doing so, you may either ask another question or exit the program.

## How It Was Done

This program was created primarily by following the guide laid out in [a blog post by Jacob Marks.](https://towardsdatascience.com/how-i-turned-my-companys-docs-into-a-searchable-database-with-openai-4f2d34bd8736) His blog was extremely helpful and informative, setting out the exact steps necessary and showing example code for much of it.

Although I followed his steps, I modified his code to suit my own needs, making use of [Qdrant's public documentation](https://qdrant.tech/documentation/) to set my code to store databases locally. Additionally, I wrote the command prompt interface and the text pre-processing personally.

## Next Steps

The future of this project is to clean the code and make it more generalizable - primarily by allowing it to function on more than just markdown files - as well as to link it to a large language model to allow it to parse the book's text to answer questions, not just return a relevant subsection of the book.