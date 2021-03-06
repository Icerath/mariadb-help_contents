#module imports
import re
import os
import datetime
import calendar

from time import perf_counter
from dataclasses import dataclass
from os.path import join as osjoin

#local imports
from page import format_to_text
#config

SQL_FILENAME: str = "new_help_tables.sql"
REGENERATE_TEXT: bool = True
DEBUG: bool = True
CURRENT_TEXT_FILES: bool = True

#set containing each text file in the fetched_pages directory
FETCHED_PAGES: list = set([file for file in os.listdir("fetched_pages") if file.endswith('txt')]) # files 
#lines need to start with this string in order to have it's description read
INSERT_INTO: str = "insert into help_topic (help_topic_id,help_category_id,name,description,example,url) values ("

#classes
@dataclass
class HelpTopic:
    """Basic container for help_topic information"""
    help_topic_id: str
    help_category_id: str
    name: str
    description: str
    example: str
    url: str
    #new description replacing old description
    new_description: str = ""

#functions
def get_name(url) -> str:
    """returns the unique text in a url eg: mariadb.com/kb/en/insert/ -> insert"""
    #reversing string
    lru = ""
    for char in url: lru = char + lru
    #finding first text inside slashes from top
    eman = re.match(r"/[\w-]+/", lru)[0].strip("/")
    #reversing name back to original order
    name = ""
    for char in eman.strip("/"): name = char + name

    return name

def get_help_topic_info(line) -> HelpTopic:
    """Returns a HelpTopic containing all the necessary information"""
    pattern = r"insert into help_topic \(help_topic_id,help_category_id,name,description,example,url\) values "
    pattern += r"\((\d+),(\d+),'(.*)','(.*)','()','(.*)'\)"
    
    return HelpTopic( *re.search(pattern, line).groups() )

def read_table_information(read_from) -> list:
    """Returns a list containing the HelpTopic from each replacable line"""
    if DEBUG: print("Reading Help Tables")
    #get lines
    with open(read_from, "r", encoding="utf-8") as infile:
        lines = infile.readlines()

    #get help topics
    gen = (get_help_topic_info(line) for line in lines if line.startswith(INSERT_INTO))
    table_information = [help_topic for help_topic in gen if help_topic.url != ""]
    #writes descriptions located in the fill_help_tables.sql file
    if CURRENT_TEXT_FILES:
        for h_topic in table_information:
            text = h_topic.description
            filename = get_name(h_topic.url) + ".txt"
            with open(osjoin("current_text_files", filename), "w", encoding="utf-8") as outfile:
                outfile.write(text.replace("\\n", "\n"))

    return table_information

def update_table_information(content: str, table_information: list) -> str:
    """Updates the new description documentation for each HelpTopic"""
    if DEBUG: print("Updating Help Tables")
    
    num_files = len(table_information)
    for index, help_topic in enumerate(table_information):
        #set new information
        name = get_name(help_topic.url)
        new_description = get_new_description(name)
        content = content.replace(help_topic.description, new_description)
        #debug progress
        if DEBUG: print(f"\rRan Through {index+1}/{num_files} files", end="")

    #replace old library url with new url
    content = content.replace("mariadb.com/kb/en/library/", "mariadb.com/kb/en/")
    #update HELP DATE's date
    content = update_help_date(content)
    #removes lines that start with 'update help'
    content = "\n".join([line for line in content.split("\n") if not line.startswith("update help")])
    
    #new line for prints after this function    
    if DEBUG: print()
    return content

def get_new_description(name):
    """Returns new description documentation for the given page name"""
    #if regenerate text bool or if txt file is not in the fetched_pages directory
    if REGENERATE_TEXT or (name + ".txt" not in FETCHED_PAGES):
        #read, convert, set new description from html file
        with open(osjoin("fetched_pages", name + ".html"), "r", encoding="utf-8") as infile:
            html = infile.read()
        new_description = format_to_text(html, name)
    else: #load text file without computation
        with open(osjoin("fetched_pages", name+".txt"), "r", encoding="utf-8") as infile:
            new_description = infile.read()
    #returns the new description with it's newlines escaped
    return "\\n".join(new_description.splitlines())

def insert_into_help_table(help_table: str, table_information: list) -> None:
    """Inserts the table information into the sql file"""
    #For each help table, replace the old description with the new description
    for help_topic in table_information:
        help_table = help_table.replace(help_topic.description, help_topic.new_description)

    #replace old library url with new url
    help_table = help_table.replace("mariadb.com/kb/en/library/", "mariadb.com/kb/en/")
    help_table = update_help_date(help_table)
    #removes lines that start with 'update help'
    help_table = "\n".join([line for line in help_table.split("\n") if not line.startswith("update help")])

    #write help table
    return help_table

def update_help_date(text: str) -> str:
    """Updates the help date to the current date"""
    #get old description
    for line in text.split("\n"):
        if line.count(",'HELP_DATE',") > 0:
            help_topic = get_help_topic_info(line)
            description = help_topic.description
            break
    #make new description
    date = datetime.date.today()
    day, month, year = date.day, calendar.month_name[date.month], date.year
    #string inputed for HELP_DATE
    updated_description = f"Help contents generated from the MariaDB Knowledge Base on {day} {month} {year}."
    #replace old with new
    text = text.replace(description, updated_description)

    return text

def main():
    """main"""
    #Create the directory 'current_text_files' if absent
    if "current_text_files" not in os.listdir(): os.makedirs("current_text_files")
    #copy fill_help_tables to new_help_tables.sql
    with open("fill_help_tables.sql", "r", encoding="utf-8") as infile: content = infile.read()
    #main processes
    table_information = read_table_information("fill_help_tables.sql")
    content = update_table_information(content, table_information)
    with open(SQL_FILENAME, "w", encoding="utf-8") as outfile: outfile.write(content)

if __name__ == "__main__":
    #keep track of 
    files = os.listdir()

    if SQL_FILENAME in files:
        with open(SQL_FILENAME, "r", encoding="utf-8") as sql_file:
            old_file = sql_file.read()
    else:
        old_file = ""

    #keep track of time
    start = perf_counter()
    #main function call
    main()
    #print changes in new_help_tables.sql
    with open(SQL_FILENAME, "r", encoding="utf-8") as sql_file:
        new_file = sql_file.read()

    if old_file == "":
        print("Wrote to", SQL_FILENAME)
    elif old_file != new_file:
        print("Updated", SQL_FILENAME)
    else:
        print("No change was made to", SQL_FILENAME)

    #manage and print time
    print("Seconds to execute:", round(perf_counter() - start, 2))