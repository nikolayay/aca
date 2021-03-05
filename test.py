from os import listdir
from os.path import isfile, join
from columnar import columnar
import assembler
from simple_processor import SimpleProcessor
import click
import time



files = [f"programs/{f}" for f in listdir("programs/") if isfile(join("programs/", f))]

tests = {
    'programs/adds_unrolled.asm': (lambda cpu: cpu.RF[1] == 90),
    'programs/adds.asm': (lambda cpu: cpu.RF[1] == 90),
    'programs/pi.asm': (lambda cpu: ''.join([str(val) for val in cpu.MEM[-8:]]) == '31415926535897932384626433832795'),
    'programs/gcd_iterative.asm': (lambda cpu: cpu.RF[0] == 30),
    'programs/bubblesort.asm': (lambda cpu: cpu.MEM == sorted([8, 14, 7, 22, 15, 1, 25, 13, 23, 24, 2, 25, 30, 9, 19, 28, 3, 23, 21, 19, 28, 24, 9, 6, 29, 12, 4, 29, 19, 24])),
    'programs/mat_mul_vec.asm': (lambda cpu: cpu.MEM[-10:] == [385, 935, 1485, 2035, 2585, 3135, 3685, 4235, 4785, 5335]),
    'programs/vector_adds.asm': (lambda cpu: cpu.MEM[-30:] == [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 0, 2, 4, 6, 8, 10, 12, 14, 16, 18]),
    'programs/vector_adds_unrolled.asm': (lambda cpu: cpu.MEM[-30:] == [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 0, 2, 4, 6, 8, 10, 12, 14, 16, 18]),
    'programs/mat_mul.asm': (lambda cpu: cpu.MEM[-64:] == [1380, 1416, 1452, 1488, 1524, 1560, 1596, 1632, 3236, 3336, 3436, 3536, 3636, 3736, 3836, 3936, 5092, 5256, 5420, 5584, 5748, 5912, 6076, 6240, 6948, 7176, 7404, 7632, 7860, 8088, 8316, 8544, 8804, 9096, 9388, 9680, 9972, 10264, 10556, 10848, 10660, 11016, 11372, 11728, 12084, 12440, 12796, 13152, 12516, 12936, 13356, 13776, 14196, 14616, 15036, 15456, 14372, 14856, 15340, 15824, 16308, 16792, 17276, 17760])
}
simple_data = []
pipelined_data = []

for ffile in files:
    try:
        with open(ffile) as f:
            program = f.readlines()
    except:
        raise RuntimeError(f"File {ffile} not found, please check path.")

    instructions, symbols = assembler.assemble(program)


    # ! simple processor tests
    cpu_simple = SimpleProcessor(instructions, symbols)

    start = time.time()
    while cpu_simple.running() :
        cpu_simple.simple_cycle()
    end = time.time()

    elapsed_simple = end - start
    simple_data.append([ffile, 
                        click.style('PASSED', fg='green') if tests[ffile](cpu_simple) else click.style('FAILED', fg='red'), 
                        "{:#.4f}".format(elapsed_simple), 
                        cpu_simple.cycles,
                        cpu_simple.executed,
                        cpu_simple.num_stalls,
                        cpu_simple.executed / cpu_simple.cycles])

    # ! pipelined processor tests
    cpu_pipelined = SimpleProcessor(instructions, symbols)
    try:
        start = time.time()
        while cpu_pipelined.running():
            cpu_pipelined.cycle_pipelined()
        end = time.time()
    except: pass

    elapsed_pipelined = end - start
    assert(cpu_pipelined.cycles == cpu_pipelined.num_stalls + cpu_pipelined.executed + 3)
    pipelined_data.append(
        [ffile, click.style('PASSED', fg='green') if tests[ffile]( cpu_pipelined) else click.style('FAILED', fg='red'), 
        "{:#.4f}".format(elapsed_pipelined),
         cpu_pipelined.cycles,
         cpu_pipelined.executed,
         cpu_pipelined.num_stalls,
         cpu_pipelined.executed / cpu_pipelined.cycles])

   

headers = ['filename', 'test result', 'elapsed (s)', 'cycles', 'instructions executed', 'num stalls', 'instructions per cycle']
simple_table = columnar(simple_data, headers, no_borders=True)
pipelined_table = columnar(pipelined_data, headers, no_borders=True)

print(simple_table)
print(pipelined_table)


