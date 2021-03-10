from os import listdir
from os.path import isfile, join
from columnar import columnar
import click
import time

import assembler
from simple_processor import SimpleProcessor
from pipelined_processor import PipelinedProcessor
from scheduled_processor import ScheduledProcessor

from tests import tests


files = [f"programs/{f}" for f in listdir("programs/") if isfile(join("programs/", f))]
processors = [SimpleProcessor, PipelinedProcessor, ScheduledProcessor]
names = [proc.__name__ for proc in processors]

simple_data = []
pipelined_data = []
tables_data = []

for processor in processors:
    data = []
    for ffile in files:
        try:
            with open(ffile) as f:
                program = f.readlines()
        except:
            raise RuntimeError(f"File {ffile} not found, please check path.")

        instructions, symbols = assembler.assemble(program)

        cpu = processor(instructions, symbols, prediction_method='one_bit', instructions_per_cycle=1)

        start = time.time()
        try:
            while cpu.running():
                cpu.cycle()
        except: pass
        end = time.time()

        elapsed_simple = end - start

        row = [ffile,
               click.style('PASSED', fg='green') if tests[ffile](
                   cpu) else click.style('FAILED', fg='red'),
               "{:#.4f}".format(elapsed_simple),
               cpu.cycles,
               cpu.executed,
               cpu.cycles / cpu.executed]
            
        if isinstance(cpu, PipelinedProcessor):
            row += [cpu.num_stalls]

        if isinstance(cpu, ScheduledProcessor):
            row += ["{:.2%}".format(cpu.predictor.prediction_accuracy())]
        
        data.append(row)

    tables_data.append(data)
   

header = ['filename', 'test result',
           'elapsed (s)', 'cycles', 'instructions executed', 'CPI']

for table_data, proc_name in zip(tables_data, names):
    if proc_name == 'ScheduledProcessor':
        h = header + ['pred accuracy']
    elif proc_name == 'PipelinedProcessor':
        h = header + ['number of stalls']
    else: h = header
    table = columnar(table_data, h, no_borders=True)
    print(click.style(proc_name, fg='cyan'))
    print(table)


