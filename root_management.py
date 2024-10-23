import os
import json

def open_root_dictionary_json():
    current_directory_path = os.path.dirname(os.path.realpath(__file__))
    root_dictionary_path = os.path.join(current_directory_path, 'root_dictionary.json')

    try:
        with open(root_dictionary_path, 'r') as root_dictionary_json:
            root_dictionary = json.load(root_dictionary_json)
        return root_dictionary
    except:
        print('root_dictionary.json not found. Creating new one...')
        with open(root_dictionary_path, 'w') as root_dictionary_json:
            root_dictionary = {}
            json.dump(root_dictionary, root_dictionary_json)
        return root_dictionary
    
def add_root_to_dictionary(root_path):
    root_dictionary = open_root_dictionary_json()
    description = input('Enter a description for this root: ')
    root_dictionary[description] = root_path

    current_directory_path  = os.path.dirname(os.path.realpath(__file__))
    root_dictionary_path = os.path.join(current_directory_path, 'root_dictionary.json')

    try:
        with open(root_dictionary_path, 'w') as root_dictionary_json:
            json.dump(root_dictionary, root_dictionary_json)
        print(f'Root {root_path} added to root_dictionary.json')
    except:
        print('Error adding root to root_dictionary.json')

