from os import listdir
from os.path import isfile, join
import assembler

files = [f for f in listdir("programs/") if isfile(join("programs/", f))]



for f in files:
    with open(f"programs/{f}") as f:
        program = f.readlines()
        assembler.assemble(program)

