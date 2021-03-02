

import re
from types import SimpleNamespace
import inspect
from copy import copy


from instruction import *

"""
Instruction fetch module. Fetch next instruction, add it to the instruction queue and increment the PC for the next cycle.
"""
class IF:
    def __init__(self, program):
        self.program = program
    
    def run(self, PC, instruction_queue):
        if PC >= len(self.program): return []
        
        if (PC > len(self.program) or PC < 0): raise RuntimeError(f"PC out of bounds. PC={PC} for program of length {len(self.program)}")
        
        instruction = self.program[PC]


        return [('set', 'PC', PC + 1), ('push', 'instruction_queue', instruction)]

"""
Decode the instruction and chuck it onto the execution queue
"""
class ID:
    def __init__(self, symbols):
        self.symbols = symbols
    
    """
    Get the top-most instruciton on the queue, decode and return
    """
    def run(self, instruction_queue, RF, execution_queue):

        updates = []
        
        if (len(instruction_queue) > 0):
            # pop off instruction  queue
           

            instruction = instruction_queue[-1]

            opcode = instruction.split()[0]
            operand_str = instruction.split(opcode)[1].strip()
            decoded_instruction = Instruction(opcode, operand_str, RF, self.symbols)

            # in any case, commit the pop
            updates.append(('pop', 'instruction_queue', None))

            # if this is a branch instruction, prepare to  
            if (decoded_instruction.branch_target):
                # branch condition is true, so we need to hop, otherwise we do nothing
                if decoded_instruction.branch_target != -1:
                    updates.append(('set', 'PC', decoded_instruction.branch_target))

                return updates
                
            # if this isnt a branch instruction then ww proceed with execution as normal
            else:
                updates.append(('push', 'execution_queue', decoded_instruction))

    
        return updates


class EX:
    def __init__(self):
        pass

    def run(self, execution_queue, memory_queue, writeback_queue):
        updates = []
       
        if (len(execution_queue) > 0):
           
            instruction = execution_queue[-1]
            target_addr, result = instruction.execute()

            # updated state
            if target_addr is not None:
                updates.append(
                    ('push', 'memory_queue', (instruction.target, target_addr, instruction.opcode)))
            if result is not None: updates.append(('push', 'writeback_queue', (instruction.target, result)))

            updates.append(('pop', 'execution_queue', None))


        return updates



class MEM:
    def __init__(self):
        pass
    def run(self, MEM, memory_queue):
        updates = []

        if (len(memory_queue) > 0):
            # we care about the opcode to distinguish between a load and a store
            register_ix, target_addr, opcode = memory_queue[-1]
            
            updates.append(('pop', 'memory_queue', None))

            if opcode == 'lw':
                updates.append(('push', 'writeback_queue', (register_ix, MEM[target_addr])))
            elif opcode == 'sw':
                updates.append(('write_mem', 'MEM', (register_ix, target_addr, opcode)))
            else:
                raise RuntimeError("Error handling a memory operation")

        return updates
class WB:
    def __init__(self):
        pass
    def run(self, RF, writeback_queue):
        updates = []
        
        if (len(writeback_queue) > 0):
           
            register_ix, result = writeback_queue[-1]

            updates.append(('pop', 'writeback_queue', None)) 
            updates.append(('write_reg', 'RF', (register_ix, result)))

       
        return updates

    
class SimpleProcessor:

    def __init__(self, program, symbols):
        self.symbols = symbols
        self.program = program
        
        self.PC = 0
       
        self.RF = [0] * 33  # (32 and an extra as a dummy for sw ROB entries)
        self.MEM = []
    
        self.cycles = 0
        self.executed = 0

        self.resolve_labels()


        # ? appear in the order they would in the diagram

        self.IF = IF(self.program)
        self.instruction_queue = []
        self.ID = ID(self.symbols)
        self.execution_queue = []
        self.EX = EX()
        self.memory_queue = []
        self.writeback_queue = []
        self._MEM = MEM()
        self.WB = WB()
        
        # self.WB = WB()

   
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


    def tick(self, updates):

        for action, attr, val, in updates:
            # print(updates)
            current = getattr(self, attr)
            if action == 'pop':
                updated = current[:-1]
                setattr(self, attr, updated)

            elif action == 'push':
                updated = [val] + current
                setattr(self, attr, updated)

            elif action == 'set':
                setattr(self, attr, val)

            elif action == 'write_reg':
                reg_target, result = val
                self.RF[reg_target] = result
                self.executed += 1

            elif action == 'write_mem':
                reg_target, target_addr, opcode = val
                
                if opcode == 'lw': self.MEM[target_addr]
                elif opcode  == 'sw': self.MEM[target_addr] =  self.RF[reg_target]
                else:
                    raise RuntimeError("Error handling a memory operation")
                self.executed += 1

            else: raise RuntimeError(f'Update type {action} not implemented')
                    
    def cycle_pipelined(self):

        updates = []
        
        update_IF = self.IF.run(
            PC=self.PC, 
            instruction_queue=self.instruction_queue            
            )
        
        update_ID = self.ID.run(
            RF=self.RF,
            instruction_queue=self.instruction_queue,
            execution_queue=self.execution_queue,
            )

        # repeat IF in case we had a branch
        # update_ID = self.IF.run(

        #     instruction_queue=self.instruction_queue,
        #     execution_queue=self.execution_queue,
        # )

        update_EX = self.EX.run(
            execution_queue=self.execution_queue,
            memory_queue=self.memory_queue,
            writeback_queue=self.writeback_queue,
        )

        update_MEM = self._MEM.run(
            MEM=self.MEM,
            memory_queue=self.memory_queue,
        )


        update_WB = self.WB.run(
            RF = self.RF,
            writeback_queue=self.writeback_queue,
        )

        
        self.cycles += 1

        updates = update_IF + update_ID + update_EX + update_MEM + update_WB
       
        
        print(f'cycle: {self.cycles}')
        print(f'IF: {update_IF}')
        print(f'ID: {update_ID}')
        print(f'EX: {update_EX}')
        print(f'MEM: {update_MEM}')
        print(f'WB: {update_WB}')
        
        # print(updates)
        self.tick(updates)

        txt = input("Press enter for next cycle")

    def simple_cycle(self):
        
        self.cycles += 1

        # Fetch
        instruction = self.fetch()

        # Decode
        instruction_decoded = self.decode(instruction)


        if (instruction_decoded.branch_target):
            # set the pc accordingly and exit this cycle because no work is left to be performed on this instruction
            if instruction_decoded.branch_target != -1: self.PC = instruction_decoded.branch_target;
            self.executed += 1
            return

        # Execute
        target_addr, result = self.execute(instruction_decoded)

        if target_addr is not None:
            result = self.mem_access(target_addr, instruction_decoded)
        
        if result is not None:
            self.write_back(result, instruction_decoded)

        self.executed += 1

    def fetch(self):
        instruction = self.program[self.PC]
        self.PC += 1
        return instruction

    def decode(self, instruction):

        opcode = instruction.split()[0]
        operand_str = instruction.split(opcode)[1].strip()

        i = Instruction(opcode, operand_str, self.RF, self.symbols)
       
        return i

    
    
    def execute(self, i):
        return i.execute()

    
    def mem_access(self, target_addr, i):
       
        if i.opcode == 'lw':
            return self.MEM[target_addr]
        elif i.opcode  == 'sw':
           self.MEM[target_addr] =  self.RF[i.target]
        else:
            raise RuntimeError("Error handling a memory operation")
        
    
    def write_back(self, result, i):
        
        self.RF[i.target] = result



    def running(self):
        return self.RF[31] != 1

    def print_stats(self):

        regs = {f"r{i}":r for i, r in enumerate(self.RF)}
        
        # print(f"REGS: {regs}\n\n")
        # print(f"MEM: {self.MEM}")

        print(f'Cycles completed: {self.cycles}')
        print(f'Instructions executed: {self.executed}')
        print(f'Instructions per cycle: {self.executed / self.cycles}')
        
