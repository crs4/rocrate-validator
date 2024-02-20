import os


def get_all_files(directory: str = '.', extension: str = '.ttl'):
    # initialize an empty list to store the file paths
    file_paths = []
    # iterate through the directory and subdirectories
    for root, dirs, files in os.walk(directory):
        # iterate through the files
        for file in files:
            # check if the file has a .ttl extension
            if file.endswith(extension):
                # append the file path to the list
                file_paths.append(os.path.join(root, file))
    # return the list of file paths
    return file_paths
