import itertools
import csv
from tests import tests
import assembler
from scheduled_processor import ScheduledProcessor
from progressbar import progressbar
from collections import Counter


"""
Produce a hude csv file for all of the programs
"""

files = [k for k in tests.keys()]


prediction_methods = ["not_taken", "one_bit", "two_bit"]
fetches_per_cycle = [1, 4]

configurations = list(itertools.product(prediction_methods, fetches_per_cycle))

opcodes = {
    "arithmetic": ["add", "sub", "mul", "mod", "div", "imul", "idiv"],
    "immediate": ["addi"],
    "memory": ["lw", "sw"],
    "branches": ["beq", "bne", "blt", "ble", "j"],
}
# header fields
fields = ["cycles", "executed", "branch_prediction_accuracy", "av_branch_distance"]

with open("log.csv", "w") as csvfile:
    cwriter = csv.writer(
        csvfile, delimiter=",", quotechar="|", quoting=csv.QUOTE_MINIMAL
    )

    # write the header
    header = ["filename"]
    for prediction_method, fetches_per_cycle in configurations:
        prefix = f"{prediction_method}_{fetches_per_cycle}"

        header += [f"{prefix}_{field}" for field in fields]

    # add the number of instriuctions
    header += list(opcodes.keys())

    cwriter.writerow(header)

    # write the data
    for ffile in progressbar(files):
        row = [ffile]

        # list of instructions in this program
        instruction_type_counter = None

        for prediction_method, fetches_per_cycle in configurations:
            prefix = f"{prediction_method}_{fetches_per_cycle}"

            try:
                with open(ffile) as f:
                    program = f.readlines()
            except:
                raise RuntimeError(f"File {ffile} not found, please check path.")

            # parsing
            instructions, symbols = assembler.assemble(program)

            # run cpu
            cpu = ScheduledProcessor(
                instructions,
                symbols,
                prediction_method=prediction_method,
                instructions_per_cycle=fetches_per_cycle,
            )

            while cpu.running():
                cpu.cycle()

            # collect metrics and write, calculate only once
            if instruction_type_counter is None:

                instruction_types = []
                for instruction in cpu.finished:
                    for k, v in opcodes.items():
                        if instruction in opcodes[k]:
                            instruction_types.append(k)

                assert len(instruction_types) == cpu.executed
                instruction_type_counter = dict(Counter(instruction_types))
                # append missing elements
                for k in opcodes.keys():
                    if k not in instruction_type_counter:
                        instruction_type_counter[k] = 0

            metrics = [
                cpu.cycles,
                cpu.executed,
                cpu.predictor.prediction_accuracy(),
                cpu.predictor.average_branch_distance(),
            ]
            # print(ffile)
            # print(prefix)
            # print(metrics)

            row += metrics

        # append calculated instruction percentages
        row += list(instruction_type_counter.values())

        cwriter.writerow(row)
