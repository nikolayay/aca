

import re
from types import SimpleNamespace
import inspect
from copy import copy
from columnar import columnar
import numpy as np
import click
import sys


from instruction import *

"""
Instruction fetch module. Fetch next instruction, add it to the instruction queue and increment the PC for the next cycle.
"""
class IF:
    def __init__(self, program, symbols, debug):
        self.debug=debug

        self.program = program
        self.symbols = symbols
    
    def run(self, PC, instruction_queue):

        if PC >= len(self.program): return []
        
        if (PC > len(self.program) or PC < 0): raise RuntimeError(f"PC out of bounds. PC={PC} for program of length {len(self.program)}")
        
        instruction_string = self.program[PC]

        instruction = Instruction(instruction_string, self.symbols, PC)

        assert(isinstance(instruction, Instruction))

        return [('set', 'PC', PC + 1), ('push', 'instruction_queue', instruction)]

"""
Decode the instruction and chuck it onto the execution queue
"""
class ID:
    def __init__(self, debug):
        self.debug = debug

        self.branch_target = None
        self.forwarded = {} # dictionary of recently forwarded register values

        self.frozen_registers = {}

        self.entry_max_age = 3


    # list of tuples of shape (reg_ix, val)
    def bypass(self, pair):
        target_register, result =  pair
        self.forwarded[target_register] = (result, self.entry_max_age)

    """
    We loop over all of the instructions and decrement the age, then delete ones with 0 age
    """
    def tick(self):

        # decrement age of forwarded registers
        
        new_forwarded = {}
        for target_register, pair in self.forwarded.items():
            result, age = pair
            new_age = age - 1

            if new_age > 0: new_forwarded[target_register] = (result, new_age)


        # keep all unfinished instructions
        new_frozen_registers = {}
        for target_register, instruction in self.frozen_registers.items():
            if not instruction.finished:
                new_frozen_registers[instruction.target_register] = instruction

        self.forwarded = new_forwarded
        self.frozen_registers = new_frozen_registers

    
    """
    Get the top-most instruciton on the queue, decode and return
    """
    def run(self, instruction_queue, RF, execution_queue):

        updates = []

        self.tick()

        if (len(instruction_queue) > 0):
            # pop off instruction  queue
        
            instruction = instruction_queue[-1]

            parsed_instruction = instruction.parse()

            if self.debug:
                print(f'currently inside ID: {parsed_instruction}')
                print(f'forwarded: {self.forwarded}')
                print(f'frozen: {self.frozen_registers}')

    
            source_regs = parsed_instruction.fetch_source_registers()

            # stalling
            # if any of source registers are in the stalled dict, push a stall onto the exec queue and return
            for source_reg in source_regs:
                if source_reg in self.frozen_registers and source_reg not in self.forwarded:

                    if self.debug: print('issuing a stall')
                   
                    return [], True

            # bypassing
            for source_reg in source_regs:
                if source_reg in self.forwarded:
                    result, age = self.forwarded[source_reg]
                    RF[source_reg] = result

            # decoding the instruction with updated register file
            decoded_instruction = parsed_instruction.read_register_file(RF)
            assert(isinstance(instruction, Instruction))

            # in any case, commit the pop
            updates.append(('pop', 'instruction_queue', None))

            # if this is a branch instruction, say we need to increment the PC
            if (decoded_instruction.branch_target):
                
                updates.append(('branch_executed', None, None))
                
                if decoded_instruction.branch_target != -1:
                    updates.append(('set', 'PC', decoded_instruction.branch_target))

                decoded_instruction.finished = True

                # todo count the branch instruction as executed

                return updates, False
                
            # if this isnt a branch instruction then we proceed with execution
            else:

                # freeze target register
                self.frozen_registers[decoded_instruction.target_register] = decoded_instruction
                updates.append(('push', 'execution_queue', decoded_instruction))


        return updates, False


class EX:
    def __init__(self, debug):
        self.debug = debug

    def run(self, execution_queue, memory_queue, writeback_queue):
        updates = []
       
        if (len(execution_queue) > 0):
           
            instruction = execution_queue[-1]
            computed_instruction = instruction.compute()

            if self.debug: print(f'currently inside EX: {computed_instruction.instruction_string}')

            # updated state
            if computed_instruction.target_address is not None:
                updates.append(
                    ('push', 'memory_queue', computed_instruction))
            if computed_instruction.result is not None: updates.append(('push', 'writeback_queue', computed_instruction))


            updates.append(('pop', 'execution_queue', None))


        return updates



class MEM:
    def __init__(self, debug):
        self.debug=debug
    def run(self, MEM, memory_queue):
        updates = []

        if (len(memory_queue) > 0):
            # we care about the opcode to distinguish between a load and a store
            instruction = memory_queue[-1]
            
            updates.append(('pop', 'memory_queue', None))

            if instruction.opcode == 'lw':
                # ! the load method fills the instruction's result field 

                instruction.result = MEM[instruction.target_address]

                # todo forward
       
                updates.append(('push', 'writeback_queue', instruction))

            elif instruction.opcode == 'sw':

                # write to memory and finish
                updates.append(('write_mem', 'MEM', instruction))
            
            else:
                raise RuntimeError("Error handling a memory operation")

        return updates
class WB:
    def __init__(self, debug):
        self.debug = debug

   
    def run(self, RF, writeback_queue):
        updates = []
        
        if (len(writeback_queue) > 0):
           
            instruction = writeback_queue[-1]

            if self.debug: print(f'currently inside WB: {instruction.instruction_string}')

            updates.append(('pop', 'writeback_queue', None)) 

            # write the register and finish
            updates.append(('write_reg', 'RF', instruction))

       
        return updates

    
class SimpleProcessor:

    def __init__(self, program, symbols, debug=False):
        self.symbols = symbols
        self.program = program
        
        self.PC = 0
       
        self.RF = [0] * 33  # (32 and an extra as a dummy for sw ROB entries)
        self.MEM = []
    
        self.cycles = 0
        self.executed = 0

        self.resolve_labels()


        # ? appear in the order they would in the diagram
        self.IF = IF(self.program, self.symbols, debug=debug)
        self.instruction_queue = []
        self.ID = ID(debug=debug)
        self.execution_queue = []
        self.EX = EX(debug=debug)
        self.memory_queue = []
        self.writeback_queue = []
        self._MEM = MEM(debug=debug)
        self.WB = WB(debug=debug)
        
        # self.WB = WB()

        # for debugging
        self.instruction_queue_history = [0] * 5
        self.execution_queue_history = [0] * 5
        self.memory_queue_history = [0] * 5
        self.writeback_queue_history = [0] * 5

        self.num_stalls = 0

        self.debug = debug

   
    def resolve_labels(self):
        clean_program = []
        # PC_offset = 0
        for line in self.program:
            if line[0] == '.': # ! a label or malloc
                label = line[1 : line.index(':')]
                values = [int(x) for x in line.split()[1:]]
                
                addr = len(self.MEM)
                self.MEM += values
                self.symbols[label] = addr # bottom address of label
                # PC_offset += 1
                
            else: # regular instruction
                clean_program.append(line)
       
        self.program = clean_program

    """
    Updating processor state each cycle
    """
    def tick(self, updates):

        for action, attr, val, in updates:
            
            if attr:current = getattr(self, attr)

            # ! keeping the history of all insgtructions for debugging
            if attr in ['instruction_queue', 'execution_queue', 'memory_queue', 'execution_queue', 'writeback_queue'] and val:
                history = getattr(self, f'{attr}_history')
                setattr(self, f'{attr}_history', [val] + history)
            
            if action == 'pop':
                updated = current[:-1]
                setattr(self, attr, updated)

            elif action == 'push':
                updated = [val] + current
                setattr(self, attr, updated)

            # this will get called every instruction fetch
            elif action == 'set':
                setattr(self, attr, val)

            elif action == 'write_reg':
                assert(isinstance(val, Instruction))
                
                instruction = val
                self.RF[instruction.target_register] = instruction.result
                self.executed += 1
                instruction.finished = True

            elif action == 'write_mem':
                assert(isinstance(val, Instruction))

                instruction = val
                if instruction.opcode != 'sw': raise RuntimeError("Error handling a memory operation")
                
                self.MEM[instruction.target_address] =  self.RF[instruction.target_register]
                self.executed += 1

                instruction.finished = True

            elif action == 'branch_executed':
                self.executed += 1


            else: raise RuntimeError(f'Update type {action} not implemented')

    # ! 3 extra cycles to process the stop
    def cycle_pipelined(self):

        self.cycles += 1
        
        
        update_IF = self.IF.run(PC=self.PC, instruction_queue=self.instruction_queue)
        
        update_ID, stalling = self.ID.run(
            RF=self.RF,
            instruction_queue=self.instruction_queue,
            execution_queue=self.execution_queue
            )

        # stall for 1 cycle
        if stalling:
            self.num_stalls += 1
            update_ID = []
            update_IF = []

        # refetch the instruction if there is a branch
        for action, attr, i in update_ID:
            if action == 'set':
                pc = i
                # new fetch
                update_IF = self.IF.run(PC=pc, instruction_queue=self.instruction_queue)
                # do not duplicate the PC update
                update_ID = update_ID[:-1]
                
            
        update_EX = self.EX.run(
            execution_queue=self.execution_queue,
            memory_queue=self.memory_queue,
            writeback_queue=self.writeback_queue,
        )


        update_MEM = self._MEM.run(MEM=self.MEM, memory_queue=self.memory_queue)


        update_WB = self.WB.run(RF = self.RF, writeback_queue=self.writeback_queue)


        # forwarding
        self.to_forward = update_EX + update_MEM
        for action, attr, i in self.to_forward:
            if action == 'push' and i.result:
                self.ID.bypass(pair=(i.target_register, i.result))
        
        # processor state update
        updates = update_IF + update_ID + update_EX + update_MEM + update_WB
        self.tick(updates)
    

        if self.debug:
            self.print_stats()
            txt = input("Press enter for next cycle")

    def simple_cycle(self):
        
        self.cycles += 1

        # Fetch
        blank_instruction = self.fetch()

        # Decode
        decoded_instruction = self.decode(blank_instruction)

        if (decoded_instruction.branch_target):
            # set the pc accordingly and exit this cycle because no work is left to be performed on this instruction
            if decoded_instruction.branch_target != -1: self.PC = decoded_instruction.branch_target;
            self.executed += 1
            return

        # Execute
        computed_instruction = decoded_instruction.compute()

        # Mem acess
        if computed_instruction.target_address is not None:
            result = self.mem_access(computed_instruction)
            computed_instruction.result = result

        # Writeback
        if computed_instruction.result is not None:
            self.write_back(computed_instruction)

    def fetch(self):
        instruction_string = self.program[self.PC]

        blank_instruction = Instruction(instruction_string, self.symbols, self.PC) 

        self.PC += 1
        return blank_instruction

    def decode(self, blank_instruction):

        parsed_instruction = blank_instruction.parse().collect_operands()

        i = parsed_instruction.read_register_file(self.RF)
       
        return i

    def execute(self, i):
        return i.execute()
 
    def mem_access(self, i):
       
        if i.opcode == 'lw':
            return self.MEM[i.target_address]
        elif i.opcode  == 'sw':
           self.MEM[i.target_address] =  self.RF[i.target_register]
           self.executed += 1

        else:
            raise RuntimeError("Error handling a memory operation")
        

    def write_back(self, i):
        self.RF[i.target_register] = i.result
        self.executed += 1


    def running(self):
        return self.RF[31] != 1

    def print_stats(self):

        queue_headers = ['name'] + [f'clock_{i}' for i in range(self.cycles, self.cycles + 5)]
        colors = ['green', 'bright_yellow', 'yellow', 'bright_red', 'red', 'black', 'black', 'black']

        def kek(i):
            if isinstance(i, Instruction):
                colour = i.colour if not i.finished else 'cyan'
                return click.style(str(i), fg=colour, bold=i.finished) 

            else:
             return click.style(str(i), fg='black')

        i_queue = ['FETCHED'] + [kek(entry) for i, entry in enumerate(self.instruction_queue_history[:5])]
        e_queue = ['EXECUTION QUEUE'] + [kek(entry) for i, entry in enumerate(self.execution_queue_history[:5])]
        m_queue = ['MEM ACCESS'] + [kek(entry) for i, entry in enumerate(self.memory_queue_history[:5])]
        w_queue = ['REGS UPDATED'] + [kek(entry) for i, entry in enumerate(self.writeback_queue_history[:5])]

        queue_data = [i_queue, e_queue, m_queue, w_queue]

        queue_table = columnar(queue_data, queue_headers, no_borders=True)

        reg_headers = [f"r{i}" for i, r in enumerate(self.RF)]
        reg_table_1 = columnar(
            [self.RF[:16]], reg_headers[:16], no_borders=True)
        reg_table_2 = columnar(
            [self.RF[16:]], reg_headers[16:], no_borders=True)

        print("\nQUEUES")
        print(f"{queue_table}\n")

        print("\nTO FORWARD")
        print(self.ID.forwarded)

        print("\nFROZEN REGISTERS")
        print(self.ID.frozen_registers)

        print("\nREGISTER FILE")
        print(f"{reg_table_1}{reg_table_2}\n")
        
        
        print(f"MEM: {self.MEM}")

        print(f'Cycles completed: {self.cycles}')
        print(f'Instructions executed: {self.executed}')
        print(f'Instructions per cycle: {self.executed / self.cycles}')
        
