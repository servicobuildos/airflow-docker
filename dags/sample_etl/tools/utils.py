import os
import shutil
import zipfile


def extractall(file_path, extract_path, overwrite=False):

    if not os.path.isfile(file_path):
        raise Exception(f'Arquivo não encontrado: {file_path}')

    if not os.path.isdir(extract_path):
        os.makedirs(extract_path)
    else:
        if overwrite:
            shutil.rmtree(extract_path)
            os.makedirs(extract_path)

    with zipfile.ZipFile(file_path) as compress_file:
        compress_file.extractall(path=extract_path)
