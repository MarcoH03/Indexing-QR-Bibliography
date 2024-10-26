import tools as t
import root_management as rm

if __name__ == '__main__':
    # at first I prompt the user for the root path to use
    root_path_dictionary = rm.open_root_dictionary_json()
    print('The root paths saved are:')
    for root_path_key, root_path in root_path_dictionary.items():
        print(f'{root_path_key} -> {root_path}')

    root_path_key = input('Enter the key for the root path you want to use or newone to add another one: ')
    
    while root_path_key.strip() == 'newone':
        root_path = input('Enter the root path you want to use: ')
        rm.add_root_to_dictionary(root_path)

        root_path_dictionary = rm.open_root_dictionary_json()
        print('The root paths saved are:')
        for root_path_key, root_path in root_path_dictionary.items():
            print(f'{root_path_key} -> {root_path}')
        
        root_path_key = input('Enter the key for the root path you want to use or newone to add another one: ') 

    root_path = root_path_dictionary[root_path_key]

    #for testing purposes I will use this root path
    # root_path = '/Users/AdrianMacAir/Desktop/Bibliografía'

    #then I update the data.json file inside that root file searching for new pdfs
    print(f'Updating data.json file in {root_path}. This may take a moment...')
    t.update_json(root_path)
    print('data.json file updated')
    
    while True:
        #then I prompt the user for the command to execute
        print('type the command you want to use or "help" to see the available commands: ')
        command = input()
        if command == 'exit':
            break
        else:
            t.manage_terminal_commands(command, root_path)
        