import json

def read_file(file:str):
    with open(file) as _data:
        data = json.load(_data)
    return data