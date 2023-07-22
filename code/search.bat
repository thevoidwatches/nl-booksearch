@echo off
:start
echo:To query an existing database, enter 'q'. To create or update one, enter 'c'.
set /p choice= "Which do you want to do? "
if "%choice%" == "q" (
    :dbChoice
    set /p db="Query which database? "
    if exist "../db/collection/%db%/" (
        :question
        set /p query= "What is your question? "
        python full.py -col %db% -q %query%
        echo:
        set /p go= "Enter 'q' to ask another question, or anything else to close. "
        if "%go%" == "q" (
            goto:question
        ) else (
            goto:end
        )
    ) else (
        echo:Database %db% not found.
        set /p go="Enter 'r' to choose a new database, or anything else to close. "
        if "%go%" == "r" (
            goto:question
        ) else (
            goto:end
        )
    )
) else (
    :bookChoice
    set /p book= "What book (in .md format) do you wish to index? "
    if exist "../%book%" (
        set /p db= "Name the database to create or update: "
        python full.py -index -col %db% -if %book% -e -index
        goto:end
    ) else (
        echo:Book %book% not found.
        set /p go="Enter 'q' to choose a database to query, or anything else to close."
        if "%go%" == "q" (
            goto:dbChoice
        ) else (
            goto:end
        )
    )
)
:end
echo:Goodbye.
pause