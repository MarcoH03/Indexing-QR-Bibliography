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


def collectPDFsInFileSystem(filePath):
    pdfs = []
    for dirpath, dirnames, filenames in os.walk(filePath):
        for filename in filenames:
            if filename.endswith('.pdf'):
                pdfs.append(os.path.join(dirpath, filename))
    return pdfs


def extractTextFromPDF(pdfPath, page_number = 0, all_pages = True):
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

def process_baic_information(text, pdf_path):
    pdf_name = ""
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

def extractBasicInformationFromText(text, pdf_path):
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
    
def add_PDF_metadata_to_json(root_path, pdf_path):
    pdf_name = pdf_path.split('/')[-1]
    root_path = os.path.join(root_path, 'data.json')
    
    try:
        with open(root_path, 'r') as file:
            data = json.load(file)

        is_new = True
        position = 0

        for pdf in data:
            if pdf['PDF_Name'] == pdf_name:
                is_new = False
                break
        if is_new:
            text = extractTextFromPDF(pdf_path)
            dictionary = extractBasicInformationFromText(text, pdf_path)
            dictionary['PDF_Name'] = pdf_name
            data.append(dictionary)
        else:
            pass
   
        with open(root_path, 'w') as file:
            json.dump(data, file, indent=4)
    except:
        with open(root_path, 'w') as file:
            text = extractTextFromPDF(pdf_path)
            dictionary = extractBasicInformationFromText(text, pdf_path)
            dictionary['PDF_Name'] = pdf_name
            json.dump([dictionary], file, indent=4)

def update_json(root_path):
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

def read_json(root_path):
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

def open_pdf(pdf_path):
    if platform.system() == 'Darwin':
        subprocess.run(['open', pdf_path], check=True)
    elif platform.system() == 'Windows':
        os.startfile(pdf_path)
    elif platform.system() == 'Linux':
        subprocess.run(['xdg-open', pdf_path], check=True)


def find_papers_by_pdf_name(pdf_name, root_path):
    data = read_json(root_path)
    saved_pdf_names = [pdf['PDF_Name'] for pdf in data]

    name_matches = process.extract(pdf_name, saved_pdf_names, scorer=fuzz.token_sort_ratio, limit=3)
    pdf_matches = [data[saved_pdf_names.index(match[0])] for match in name_matches]
    
    return pdf_matches

def find_papers_by_paper_name(paper_name, root_path):
    data = read_json(root_path)
    saved_paper_names = [pdf['Title'] for pdf in data]

    title_matches = process.extract(paper_name, saved_paper_names, scorer=fuzz.token_sort_ratio, limit=3)
    pdf_matches = [data[saved_paper_names.index(match[0])] for match in title_matches]
    
    return pdf_matches

def find_papers_by_author(authors, root_path):
    data = read_json(root_path)
    saved_authors = [pdf['Authors'] for pdf in data]

    author_matches = process.extract(authors, saved_authors, scorer=fuzz.partial_ratio, limit=3)
    pdf_matches = [data[saved_authors.index(match[0])] for match in author_matches]
    
    return pdf_matches

def find_papers_by_keywords(keywords, root_path):
    data = read_json(root_path)
    saved_keywords = [pdf['Keywords'] for pdf in data]

    keyword_matches = process.extract(keywords, saved_keywords, scorer=fuzz.partial_ratio, limit=3)
    pdf_matches = [data[saved_keywords.index(match[0])] for match in keyword_matches]
    
    return pdf_matches

def find_papers_by_mentions(mentions, root_path):
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

def show_find_results(pdf_matches):
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
    #temporalmente. Esto es para ver si funciona el open_pdf
    command = input('Do you want to open any of the PDFs? (y/n): ')
    if command == 'y':
        pdf_number = int(input('Enter the number of the PDF you want to open: '))
        open_pdf(pdf_matches[pdf_number-1]['PDF_Path'])
    



