
import itertools
import csv
from tests import tests
import assembler
from scheduled_processor import ScheduledProcessor
from progressbar import progressbar


"""
Produce a hude csv file for all of the programs
"""

files = [k for k in tests.keys()]


prediction_methods = ['not_taken', 'one_bit', 'two_bit']
fetches_per_cycle = [1, 4]

configurations = list(itertools.product(prediction_methods, fetches_per_cycle))

fields = ['cycles', 'executed', 'prediction_accuracy']

with open('log.csv', 'w') as csvfile:
    cwriter = csv.writer(csvfile, delimiter=',',
                         quotechar='|', quoting=csv.QUOTE_MINIMAL)

    # write the header
    header = ['filename']
    for prediction_method, fetches_per_cycle in configurations:
        prefix = f'{prediction_method}_{fetches_per_cycle}'

        header += [f'{prefix}_{field}' for field in fields]
    
    cwriter.writerow(header)

    # write the data
    for ffile in progressbar(files):
        row = [ffile]

        # todo calc instruction percentages
        for prediction_method, fetches_per_cycle in configurations:
            prefix = f'{prediction_method}_{fetches_per_cycle}'
            
            try:
                with open(ffile) as f:
                    program = f.readlines()
            except:
                raise RuntimeError(f"File {ffile} not found, please check path.")
            
            # parsing
            instructions, symbols = assembler.assemble(program)

            # run cpu
            cpu = ScheduledProcessor(
                instructions, symbols, prediction_method=prediction_method, instructions_per_cycle=fetches_per_cycle
            )

            try:
                while cpu.running():
                    cpu.cycle()
            except:
                pass
                
            # collect metrics and write
            


            metrics = [
                cpu.cycles,
                cpu.executed,
                cpu.predictor.prediction_accuracy()
            ]
            print(ffile)
            print(prefix)
            print(metrics)

            row += metrics

        
        cwriter.writerow(row)

