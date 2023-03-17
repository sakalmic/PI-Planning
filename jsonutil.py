import json


def readfromfile(fn):
    with open(fn) as file:
        return json.load(file)


def writetofile(fn, x):
    with open(fn, "w") as file:
        json.dump(x, file, indent=4)
