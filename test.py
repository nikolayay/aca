from os import listdir
from os.path import isfile, join
from columnar import columnar
import argparse
from progressbar import progressbar
import click
import time

import assembler
from simple_processor import SimpleProcessor
from pipelined_processor import PipelinedProcessor
from scheduled_processor import ScheduledProcessor

from tests import tests

parser = argparse.ArgumentParser(description="Run the test suite for all programs")

parser.add_argument(
    "-s",
    required=True,
    help="Superscalar factor",
    type=int,
    dest="instructions_per_cycle",
)

parser.add_argument(
    "-pred",
    "--predictor",
    required=True,
    help="Choose the branch prediction method.",
    choices=["taken", "not_taken", "one_bit", "two_bit"],
    dest="prediction_method",
)

args = parser.parse_args()


files = [k for k in tests.keys()]
processors = [SimpleProcessor, PipelinedProcessor, ScheduledProcessor]
names = [proc.__name__ for proc in processors]
tables_data = []

for processor in progressbar(processors):
    data = []
    for ffile in files:
        try:
            with open(ffile) as f:
                program = f.readlines()
        except:
            raise RuntimeError(f"File {ffile} not found, please check path.")

        instructions, symbols = assembler.assemble(program)

        cpu = processor(
            instructions,
            symbols,
            prediction_method=args.prediction_method,
            instructions_per_cycle=args.instructions_per_cycle,
        )

        start = time.time()

        while cpu.running():
            cpu.cycle()

        end = time.time()

        elapsed_simple = end - start

        row = [
            ffile,
            click.style("PASSED", fg="green")
            if tests[ffile](cpu)
            else click.style("FAILED", fg="red"),
            "{:#.4f}".format(elapsed_simple),
            cpu.cycles,
            cpu.executed,
            cpu.cycles / cpu.executed,
        ]

        if isinstance(cpu, PipelinedProcessor):
            row += [cpu.num_stalls]

        if isinstance(cpu, ScheduledProcessor):
            row += [cpu.predictor.prediction_accuracy()]

        data.append(row)

    tables_data.append(data)


header = [
    "filename",
    "test result",
    "elapsed (s)",
    "cycles",
    "instructions executed",
    "CPI",
]

for table_data, proc_name in zip(tables_data, names):
    if proc_name == "ScheduledProcessor":
        h = header + ["branch prediction accuracy"]
    elif proc_name == "PipelinedProcessor":
        h = header + ["number of stalls"]
    else:
        h = header
    table = columnar(table_data, h, no_borders=True)
    print(click.style(proc_name, fg="cyan"))
    print(table)
