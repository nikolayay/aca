import assembler
import argparse
from simple_processor import SimpleProcessor

parser = argparse.ArgumentParser(description='Produce a binary .dat file from a .txt assembly code')
parser.add_argument("-v", "--verbose", help="increase output verbosity",
                action="store_true")

parser.add_argument("-f", "--file", dest="filename", required=True,
                help="input file with MIPS assembly code",
                type=argparse.FileType())

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

print(instructions, symbols)
i = 0
while cpu.running() :
    cpu.cycle()
    i += 1

cpu.print_stats()
