import pdfplumber
import json
from whoosh.index import create_in
from whoosh.qparser import QueryParser
from whoosh.fields import Schema, TEXT, KEYWORD, ID
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import os
import time 
import platform
import subprocess
import google.generativeai as genai
import re

def implement_funcion():
    print("la funcion que llamas no esta' implementada")
    return None

def collectPDFsInFileSystem(filePath): #searches for all pdf's path inside the main folder you give it
    pdfs = []
    for dirpath, dirnames, filenames in os.walk(filePath):
        for filename in filenames:
            if filename.endswith('.pdf'):
                pdfs.append(os.path.join(dirpath, filename))
    return pdfs


def extractTextFromPDF(pdfPath, page_number = 0, all_pages = True): #takes if you want to process a page or the whole pdf and returns all the text in that part as a string
    with pdfplumber.open(pdfPath) as pdf:
        if all_pages:
            disordered_text = ''
            for i in range(len(pdf.pages)):
                page = pdf.pages[i]
                disordered_words = page.extract_words(use_text_flow=True)

                for word in disordered_words:
                    disordered_text += word['text'] + ' '
        else:
            disordered_text = ''
            page = pdf.pages[page_number]
            disordered_words = page.extract_words(use_text_flow=True)
            
            for word in disordered_words:
                disordered_text += word['text'] + ' '
       
        return disordered_text

def process_baic_information(text, pdf_path): #it takes a string with the information and the pdf path to then process the string and return a dictionary with the sorted information
    pdf_name = pdf_path.split('/')[-1]
    title = text.split('"Title":')[1].split('"Authors":')[0]
    authors = text.split('"Authors":')[1].split('"Keywords":')[0]
    keywords = text.split('"Keywords":')[1].split('"Problem":')[0]
    problem = text.split('"Problem":')[1].split('"Method":')[0]
    method = text.split('"Method":')[1].split('"Results":')[0]
    results = text.split('"Results":')[1]

    processed_response = {
        'PDF_Name': pdf_name,
        'PDF_Path': pdf_path,
        'Title': title,
        'Authors': authors,
        'Keywords': keywords,
        'Problem': problem,
        'Method': method,
        'Results': results
    }
    return processed_response

def extractBasicInformationFromText(text, pdf_path): #it takes the text and the pdf path then preocesses the text with gemini, passes the output to the process_basic_info function and returns the dictionary with the sorted info
    gemini_api_key = os.getenv('GEMINI_API_KEY')

    if gemini_api_key is None:
        raise ValueError("API key not found")
    else:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = 'The following text is from an academic paper. From it extract the title, authors, keywords, the scientific problem they try to solve, the method they use to solve it and the results they obtained. Structure the answer like: "Title":[...] "Authors":[...] "Keywords":[...] "Problem":[...] "Method":[...] "Results":[...]. For each parameter write the answer in plain text with a simple structure. Do not add any extra text. If it is in spanish make the answers in spanish as well. The text is: ' + text
        print('total_tokens:', model.count_tokens(prompt))
        response = model.generate_content(prompt)
        print(response.text)

        return process_baic_information(response.text, pdf_path)
    
def add_PDF_metadata_to_json(root_path, pdf_path): # it takes a root_path where the json would be and the pdf path, then processes the pdf data to get the dictionary with sorted info and tries to save the info in an existing json. If it doesnt exit it creates a new one. If the data for the pdf exists then it doesn't add anything
    pdf_name = pdf_path.split('/')[-1]
    root_path = os.path.join(root_path, 'data.json')
    
    try:
        with open(root_path, 'r') as file:
            data = json.load(file)

        is_new = True

        for pdf in data:
            if pdf['PDF_Name'] == pdf_name:
                is_new = False
                break
        if is_new:
            text = extractTextFromPDF(pdf_path)
            dictionary = extractBasicInformationFromText(text, pdf_path)
            data.append(dictionary)
        else:
            pass
   
        with open(root_path, 'w') as file:
            json.dump(data, file, indent=4)
    except:
        with open(root_path, 'w') as file:
            text = extractTextFromPDF(pdf_path)
            dictionary = extractBasicInformationFromText(text, pdf_path)
            json.dump([dictionary], file, indent=4)

def update_json(root_path): # checks if there are new files in the folders and if there are then it uses the add_pdf_metadata_to_json function to add ther info
    pdfs = collectPDFsInFileSystem(root_path)

    try:
        with open(os.path.join(root_path, 'data.json'), 'r') as file:
            data = json.load(file)
        pdfs_in_json = [pdf['PDF_Name'] for pdf in data]
        for pdf in pdfs:
            if pdf.split('/')[-1] in pdfs_in_json:
                continue
            else:
                time.sleep(3) #there's a 15 request per minute limit
                add_PDF_metadata_to_json(root_path, pdf)
    except:
        for pdf in pdfs:
            time.sleep(3)
            add_PDF_metadata_to_json(root_path, pdf)

def read_json(root_path): # it tries to find the json with the data. If it exist it returns the list of dictionaries stored there. If it doesn't it creates one and returns an empty list
    root_path = os.path.join(root_path, 'data.json')
    try:
        with open(root_path, 'r') as file:
            data = json.load(file)
        return data
    except:
        print('No data found')
        print('Creating new json file')
        with open(root_path, 'w') as file:
            json.dump([], file, indent=4)
        return []

def open_pdf(pdf_path): #opens the pdf in the given path. Works on windows, macos and linux
    if platform.system() == 'Darwin':
        subprocess.run(['open', pdf_path], check=True)
    elif platform.system() == 'Windows':
        os.startfile(pdf_path)
    elif platform.system() == 'Linux':
        subprocess.run(['xdg-open', pdf_path], check=True)

#region Terminal Commands
def find_papers_by_pdf_name(pdf_name, root_path): # searches for papers by the name of the pdf and returns the dictionaries of the found pdfs
    data = read_json(root_path)
    saved_pdf_names = [pdf['PDF_Name'] for pdf in data]

    name_matches = process.extract(pdf_name, saved_pdf_names, scorer=fuzz.token_sort_ratio, limit=3)
    pdf_matches = [data[saved_pdf_names.index(match[0])] for match in name_matches]
    
    return pdf_matches

def find_papers_by_paper_title(paper_name, root_path): # searches for papers by the title of the paper and returns the dictionaries of the found pdfs
    data = read_json(root_path)
    saved_paper_names = [pdf['Title'] for pdf in data]

    title_matches = process.extract(paper_name, saved_paper_names, scorer=fuzz.token_sort_ratio, limit=3)
    pdf_matches = [data[saved_paper_names.index(match[0])] for match in title_matches]
    
    return pdf_matches

def find_papers_by_author(authors, root_path): # searches for papers by the name of the authors and returns the dictionaries of the found pdfs
    data = read_json(root_path)
    saved_authors = [pdf['Authors'] for pdf in data]

    author_matches = process.extract(authors, saved_authors, scorer=fuzz.partial_ratio, limit=3)
    pdf_matches = [data[saved_authors.index(match[0])] for match in author_matches]
    
    return pdf_matches

def find_papers_by_keywords(keywords, root_path): # searches for papers by keywords and returns the dictionaries of the found pdfs
    data = read_json(root_path)
    saved_keywords = [pdf['Keywords'] for pdf in data]

    keyword_matches = process.extract(keywords, saved_keywords, scorer=fuzz.partial_ratio, limit=3)
    pdf_matches = [data[saved_keywords.index(match[0])] for match in keyword_matches]
    
    return pdf_matches

def find_papers_by_mentions(mentions, root_path): # searches for papaers that contains sertain words or phrases and returns the dictionaries of the found pdfs
    data = read_json(root_path)
    saved_mentions = []
    pdf_paths = [pdf['PDF_Path'] for pdf in data]
    for pdf_path in pdf_paths:
        text = extractTextFromPDF(pdf_path)
        mention_matches = [matches for matches in process.extract(mentions, text, scorer=fuzz.partial_ratio) if matches[1]>60]
        saved_mentions.append([pdf_path,len(mention_matches)])

    pdf_matches = [(data[pdf_paths.index(mention[0])], mention[1]) for mention in saved_mentions]
    pdf_matches = sorted(pdf_matches, key=lambda x: x[1], reverse=True)
    pdf_matches = [pdf[0] for pdf in pdf_matches]
    
    return pdf_matches

def show_find_results(pdf_matches): # in a list of pdf metadata dictionaries it prints the info of every dictinary
    print("RESULTS:")
    for index, pdf in enumerate(pdf_matches):
        print(f'PDF {index+1}:')
        print('   PDF Name:', pdf['PDF_Name'])
        print('   Title:', pdf['Title'])
        print('   Authors:', pdf['Authors'])
        print('   Keywords:', pdf['Keywords'])
        print('   Problem:', pdf['Problem'])
        print('   Method:', pdf['Method'])
        print('   Results:', pdf['Results'])
        print('-------------------')
    
def open_pdf_name(pdf_name, root_path): #searches for a pdf by the name of the pdf and opens it
    pdf_matches = find_papers_by_pdf_name(pdf_name, root_path)
    pdf_path = pdf_matches[0]['PDF_Path']
    open_pdf(pdf_path)

def open_paper_title(paper_name, root_path): #searches for a pdf by the title of the paper and opens it
    pdf = find_papers_by_paper_title(paper_name, root_path)
    pdf_path = pdf['PDF_Path']
    open_pdf(pdf_path)

def manually_edit_pdf(pdf): #it takes a dictionary with the pdf metadata and lets you edit the info returning the modified info
    print('What do you want to edit?')
    print('1. Title')
    print('2. Authors')
    print('3. Keywords')
    print('4. Problem')
    print('5. Method')
    print('6. Results')
    selection = int(input('Enter the number of the parameter you want to edit: '))
    
    if selection == 1:
        print('Current Title:', pdf['Title'])
        new_title = input('Enter the new title: ')
        confirmation = input(f'Are you sure you want to change the title to "{new_title}"? (y/n): ')
        if confirmation == 'y':
            pdf['Title'] = new_title
        elif confirmation == 'n':
            print('Title not changed')
    if selection == 2:
        print('Current Authors:', pdf['Authors'])
        new_authors = input('Enter the new authors: ')
        confirmation = input(f'Are you sure you want to change the authors to "{new_authors}"? (y/n): ')
        if confirmation == 'y':
            pdf['Authors'] = new_authors
        elif confirmation == 'n':
            print('Authors not changed')
    if selection == 3:
        print('Current Keywords:', pdf['Keywords'])
        new_keywords = input('Enter the new keywords: ')
        confirmation = input(f'Are you sure you want to change the keywords to "{new_keywords}"? (y/n): ')
        if confirmation == 'y':
            pdf['Keywords'] = new_keywords
        elif confirmation == 'n':
            print('Keywords not changed')
    if selection == 4:
        print('Current Problem:', pdf['Problem'])
        new_problem = input('Enter the new problem: ')
        confirmation = input(f'Are you sure you want to change the problem to "{new_problem}"? (y/n): ')
        if confirmation == 'y':
            pdf['Problem'] = new_problem
        elif confirmation == 'n':
            print('Problem not changed')
    if selection == 5:
        print('Current Method:', pdf['Method'])
        new_method = input('Enter the new method: ')
        confirmation = input(f'Are you sure you want to change the method to "{new_method}"? (y/n): ')
        if confirmation == 'y':
            pdf['Method'] = new_method
        elif confirmation == 'n':
            print('Method not changed')
    if selection == 6:
        print('Current Results:', pdf['Results'])
        new_results = input('Enter the new results: ')
        confirmation = input(f'Are you sure you want to change the results to "{new_results}"? (y/n): ')
        if confirmation == 'y':
            pdf['Results'] = new_results
        elif confirmation == 'n':
            print('Results not changed')
    
    return pdf


def edit_pdf_name(pdf_name, root_path): #searches for a pdf by the name of the pdf and allows to edit it's parameters
    pdf_matches = find_papers_by_pdf_name(pdf_name, root_path)
    print('Select which one to edit:')
    show_find_results(pdf_matches)
    selection = int(input('Enter the number of the pdf you want to edit: '))
    pdf = pdf_matches[selection-1]
    manually_edit_pdf(pdf)

    root_path = os.path.join(root_path, 'data.json')

    with open(root_path, 'w') as file:
            data = json.load(file)
            data[selection-1] = pdf
            json.dump(data, file, indent=4)
    print("Changes saved")

def edit_paper_title(paper_title, root_path): #searches for a pdf by the title of the paper and allows to edit it's parameters
    pdf_matches = find_papers_by_paper_title(paper_title, root_path)
    print('Select which one to edit:')
    show_find_results(pdf_matches)
    selection = int(input('Enter the number of the pdf you want to edit: '))
    pdf = pdf_matches[selection-1]
    manually_edit_pdf(pdf)

    root_path = os.path.join(root_path, 'data.json')

    with open(root_path, 'w') as file:
            data = json.load(file)
            data[selection-1] = pdf
            json.dump(data, file, indent=4)
    print("Changes saved")

def manage_terminal_commands(full_command, root_path):

    names_of_terminal_commands = {
        'find_pdf_name': find_papers_by_pdf_name,
        'find_paper_title': find_papers_by_paper_title,
        'find_authors': find_papers_by_author,
        'find_keywords': find_papers_by_keywords,
        'find_mentions': find_papers_by_mentions,

        'open_pdf_name': open_pdf_name,
        'open_paper_title': open_paper_title,

        'edit_pdf_name': edit_pdf_name,
        'edit_paper_title': edit_paper_title
    }

    full_command = full_command.strip()
    full_command = full_command.split(":")
    command_name = full_command.pop(0)
    assert command_name in names_of_terminal_commands, 'Unknown Command'
    command = names_of_terminal_commands[command_name]
    parameters = full_command[0]
    parameters = parameters.strip() if parameters else None

    #use regular expression to catch if the command starts with find, opne or edit
    pattern = r'^([a-zA-Z]*)_([a-zA-Z]*(?:_[a-zA-Z]*)*)$'
    command_name_structure = re.match(pattern, command_name)
    command_sub_name, specific_name = command_name_structure.groups()
    if command_sub_name == 'find':
        if parameters:
            command(parameters, root_path)
        else:
            print('You need to enter a parameter to find a paper')
    elif command_sub_name == 'open':
        if parameters:
            command(parameters, root_path)
        else:
            print('You need to enter a parameter to open a paper')
    elif command_sub_name == 'edit':
        if parameters:
            command(parameters, root_path)
        else:
            print('You need to enter a parameter to edit a paper')
    else:
        print("Don't know how but this sub command doesn't exist")

#endregion Terminal Commands

