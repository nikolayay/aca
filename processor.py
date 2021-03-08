import re
import sys
import click
from instruction import *


class Processor:

    def __init__(self, program, symbols, debug=False):
        self.symbols = symbols
        self.program = program

        self.PC = 0

        self.MEM = []

        self.cycles = 0
        self.executed = 0
        self.num_stalls = 0
        self.resolve_labels()


        self.debug = debug

    def resolve_labels(self):
        clean_program = []
        # PC_offset = 0
        for line in self.program:
            if line[0] == '.':  # ! a label or malloc
                label = line[1: line.index(':')]
                values = [int(x) for x in line.split()[1:]]

                addr = len(self.MEM)
                self.MEM += values
                self.symbols[label] = addr  # bottom address of label
                # PC_offset += 1

            else:  # regular instruction
                clean_program.append(line)

        self.program = clean_program

    def cycle(self):
        # to be overloaded by children
        pass

    
    def running(self):
        return self.RF[31] != 1

    def print_stats(self):
        pass
