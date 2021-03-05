import argparse
import assembler
from simple_processor import SimpProcessor
from pipelined_processor import PipelinedProcessor

parser = argparse.ArgumentParser(description='Run a processor simulation for a given assembly program.')

parser.add_argument("-f", "--file", dest="filename", required=True,
                help="Provide a path for the assembly program found in programs/ folder.",
                type=argparse.FileType())

parser.add_argument("-p", "--processor", required=True,
                    help="Choose the kind of processor to simulate. Currently supports simple unpipelined and stalled pipeline processors",
                    choices=['simple', 'pipelined'],
                    dest='processor_type'
                    )

parser.add_argument("-d", "--debug", dest='debug', action='store_true', default=False, help='Debug mode to enable logging output and stepping throught the execution.')

args = parser.parse_args()

try:
    with open(args.filename.name) as f:
        program = f.readlines()
except:
    raise RuntimeError(f"File {args.filename.name} not found, please check path.")


instructions, symbols = assembler.assemble(program)


if args.processor_type == 'simple':
    processor = SimpProcessor
elif args.processor_type == 'pipelined':
    processor = PipelinedProcessor
else: raise RuntimeError("Processor type not implemented")



cpu = processor(instructions, symbols, debug=args.debug)

# print(instructions, symbols)

while cpu.running():
    cpu.cycle()


cpu.print_stats()
