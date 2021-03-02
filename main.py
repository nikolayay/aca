import assembler
import argparse
from simple_processor import SimpleProcessor

parser = argparse.ArgumentParser(description='Produce a binary .dat file from a .txt assembly code')
parser.add_argument("-v", "--verbose", help="increase output verbosity",
                action="store_true")

parser.add_argument("-f", "--file", dest="filename", required=True,
                help="input file with MIPS assembly code",
                type=argparse.FileType())

parser.add_argument("-p", "--processor", required=True,
                    help="Provide the kind of the simulated processor",
                    choices=['simple', 'pipelined'],
                    dest='processor_type'
                    )

args = parser.parse_args()
if args.verbose:
    logging.basicConfig(level=logging.DEBUG)

try:
    with open(args.filename.name) as f:
        program = f.readlines()
except:
    raise RuntimeError(f"File {args.filename.name} not found, please check path.")


instructions, symbols = assembler.assemble(program)
cpu = SimpleProcessor(instructions, symbols)

# print(instructions, symbols)

while cpu.running():
    if args.processor_type=='simple': cpu.simple_cycle()
    elif args.processor_type == 'pipelined': cpu.cycle_pipelined()
    else: raise RuntimeError("Processor type not implemented")


cpu.print_stats()
