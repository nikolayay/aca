arithmetic = ['add', 'sub', 'mul', 'mod', 'div', 'imul', 'idiv']
immediate = ['addi']
memory = ['lw', 'sw']
branches = ['beq', 'bne', 'blt', 'ble']
jumps = ['j']

import re


class Instruction:
    def __init__(self, opcode, operand_str, RF, symbols):
        self.opcode = opcode
        self.operand_str = operand_str
        self.symbols = symbols
        self.branch_target = None
        
        if self.opcode in arithmetic:
            

            operands = self.parse_operands("^(?P<rd>\$\w*) (?P<rs>\$\w*) (?P<rt>\$\w*)$")
            
            # prefetching
            self.target = operands['rd']
            self.rs = RF[operands['rs']]
            self.rt = RF[operands['rt']]

        elif self.opcode in immediate:
           
            
            operands = self.parse_operands("^(?P<rt>\$\w*) (?P<rs>\$\w*) (?P<imm>-*\d+)$")
            
            # prefetching
            self.target = operands['rt']
            self.rs = RF[operands['rs']]
            self.imm = operands['imm']

        elif self.opcode in memory:
           
            
            operands = self.parse_operands("^(?P<rt>\$\w*) *(?P<imm>\w+)\((?P<rs>\$\w*|\d*)\)$")
            
            # prefetching
            self.target = operands['rt']
            self.rs = RF[operands['rs']]
            self.imm = operands['imm']

            
        elif self.opcode in branches:
            
            operands = self.parse_operands("^(?P<rs>\$\w*) (?P<rt>\$\w*) (?P<imm>-*\d+|\$*\w*)$")
            
            # prefetching
            self.rs = RF[operands['rs']]
            self.rt = RF[operands['rt']]
            self.imm = operands['imm']
            
            self.evaluate_registers()

        elif self.opcode in jumps:

            operands = self.parse_operands("^(?P<imm>\w*)$")
            
            # prefetching
            self.imm = operands['imm']
            
            self.evaluate_registers()

        else: raise RuntimeError(f"Decode of {self.opcode} {self.operand_str} -> Not implemented")

    def parse_operands(self, pattern):
        match = re.match(pattern, self.operand_str)
        if not match: raise RuntimeError(f"Match broken for instruction {self.opcode} {self.operand_str}")

        operands = {}
        
        for k, v in match.groupdict().items():
            if v in self.symbols: operands[k] = self.symbols[v]
            elif v[0] == '$': operands[k] = int(v[1:])
            else: operands[k] = int(v)     
        
        return operands

    # set the branch target address if the branch condition evaluated to true:
    # if false just go to the next instruction
    def evaluate_registers(self):
        if self.opcode not in branches + jumps: 
            raise RuntimeError(f"You should not be calling this method when processing the instruction {self.opcode} {self.operand_str}")
        
        if self.opcode == 'beq':
            if (self.rs == self.rt):
                self.branch_target = self.imm;
            else: self.branch_target = -1

        elif self.opcode == 'blt':
            if (self.rs < self.rt):
                self.branch_target = self.imm;
            else: self.branch_target = -1

        elif self.opcode == 'ble':
            if (self.rs <= self.rt):
                self.branch_target = self.imm;
            else: self.branch_target = -1

        elif self.opcode == 'j':
            self.branch_target = self.imm;
        
        else:
            raise RuntimeError(f"Branch evaluate of {self.opcode} -> Not implemented")

    # returns a target_address and the result and a branch target
    def execute(self):
        if self.opcode in branches + jumps:
            raise RuntimeError("You should not call execute on branch or jump instructions")

        if self.opcode == 'add':
            return None, self.rs + self.rt

        elif self.opcode == 'sub':
            return None, self.rs - self.rt

        elif self.opcode == 'mul':
            return None, self.rs * self.rt

        elif self.opcode == 'imul':
            return None, int(int(self.rs) * int(self.rt))

        elif self.opcode == 'mod':
            return None, int(int(self.rs) % int(self.rt))

        elif self.opcode == 'div':
            return None, self.rs / self.rt

        elif self.opcode == 'idiv':
            return None, int(int(self.rs) / int(self.rt))

        elif self.opcode == 'addi':
            return None, self.rs + self.imm

        elif self.opcode == 'lw' or self.opcode == 'sw':
            return self.rs + self.imm, None

        else:
            raise RuntimeError(f"Execute of {self.opcode} -> Not implemented")


class SimpleProcessor():

    def __init__(self, program, symbols):
        self.program = program
        self.symbols = symbols
        
        self.PC = 0
       
        self.RF = [0] * 33  # (32 and an extra as a dummy for sw ROB entries)
        self.MEM = []
    
        self.cycles = 0
        self.executed = 0

    def cycle(self):
        
        # Fetch
        instruction = self.fetch()

        # Decode
        instruction_decoded = self.decode(instruction)


        if (instruction_decoded.branch_target):
            # skipping the rest if we don't need to branch (target == -1)
            if instruction_decoded.branch_target > 0: self.PC = instruction_decoded.branch_target;
            return

        # Execute
        target_addr, result = self.execute(instruction_decoded)


        if target_addr is not None:
            result = self.mem_access(target_addr, instruction_decoded)
        
        if result is not None:
            self.write_back(result, instruction_decoded)

       

    def fetch(self):
        instruction = self.program[self.PC]
        self.PC += 1
        return instruction

    def decode(self, instruction):
              
        if instruction[0] == '.': # ! a label or malloc
            label = instruction[1 : instruction.index(':')]
            values = [int(x) for x in instruction.split()[1:]]
            
            addr = len(self.MEM)
            self.MEM += values
            self.symbols[label] = addr # bottom address of label
            
            opcode = 'add'
            operand_str = '$32 $32 $32'
        else: # regular instruction
            opcode = instruction.split()[0]
            operand_str = instruction.split(opcode)[1].strip()
            
        # read the registers
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

        # if len(self.wbq) > 0:
        #     # Only write back if it has been enough cycles
        #     if self.wbq[0][2] <= 0 and self.wbq[0][4] < 0:
        #         # 1. Broadcast the name (or tag) and the value of the completed instruction
        #         #    back to the rs so that the rs can 'capture' the values.
        #         tag, val, cycles, op, allowed = self.wbq.pop(0)
        #         self.rs.capture(tag, val)
        #         self.lsq.capture(tag, val)
        #         # 2. Place the broadcast value into the rob_entry used for that instruction.
        #         #    Set rob_entry.done to True
        #         self.rob.entries[tag].val = val
        #         self.rob.entries[tag].done = True
        # # Commit
        # # 1. Test if next instruction at commit pointer of rob is done.
        # # 2. If it is done, commit:
        # #        a. Write the rob_entry.val to the rob_entry.reg.
        # #        b. If rob_entry is latest rename of rat for rob_entry.reg,
        # #               update rat to point to rob_entry.reg instead of rob_entry
        # #           else:
        # #               leave rat entry as is
        # rob_entry = self.rob.entries[self.rob.commit]
        # load = rob_entry.load
        # branch = rob_entry.branch
        # if rob_entry.done == True:
        #     self.rf[rob_entry.reg] = rob_entry.val
        #     if self.rat[rob_entry.reg] == self.rob.commit:
        #         self.rat[rob_entry.reg] = None
        #     self.rob.entries[self.rob.commit] = ROB.ROB_entry()
        #     self.rs.capture(self.rob.commit, rob_entry.val)
        #     self.lsq.capture(self.rob.commit, rob_entry.val)
        #     self.rob.commit += 1
        #     if self.rob.commit == len(self.rob.entries):
        #         self.rob.commit = 0
        #     if load:
        #         lsq_entry = self.lsq.entries[self.lsq.commit]
        #         if lsq_entry.op == 'sw':
        #             self.mem[lsq_entry.addr] = self.rf[lsq_entry.reg]
        #         elif lsq_entry.op == 'lw':
        #             self.rf[rob_entry.reg] = self.mem[lsq_entry.addr]
        #         self.lsq.entries[self.lsq.commit] = LSQ.LSQ_entry()
        #         self.lsq.entries[self.lsq.commit].complete = True
        #         self.lsq.commit += 1
        #     if branch:
        #         correct, pc = self.predictor.check(
        #             self.rf,
        #             rob_entry.op,
        #             rob_entry.operands,
        #             rob_entry.current_pc,
        #             rob_entry.next_pc,
        #             self.executed,
        #         )
        #         if not correct:
        #             self.iq = []
        #             self.opq = []
        #             self.rob = ROB(self.rob_size)
        #             array_labels = self.lsq.array_labels
        #             self.lsq = LSQ()
        #             self.lsq.array_labels = array_labels
        #             self.rat = [None] * 128
        #             self.rs = RS()
        #             self.eq = []
        #             self.wbq = []
        #             self.pc = pc
        #             self.new_iq = []
        #             self.new_opq = []
        #             self.new_eq = []
        #     self.executed += 1


    def running(self):
        return self.RF[31] != 1

    def print_stats(self):

        regs = {f"r{i}":r for i, r in enumerate(self.RF)}
        
        print(f"REGS: {regs}\n\n")
        print(f"MEM: {self.MEM}")

        # print(f'cycle: {self.cycles}')
        # print(f'executed: {self.executed}')
        # print(f'instruction queue: {self.iq}')
        # print(f'op queue: {self.opq}')
        # print(f'register file: {self.rf}')
        # print(f'rob: { [f"{e.reg}, {e.val}, {e.done}" for e in self.rob.entries[:10]] }')
        # print(
        #     f'lsq: { [f"{e.op}, {e.dest_tag}, {e.addr}, {e.val}, {e.done}" for e in self.lsq.entries[:10]] }'
        # )
        # print(f'rat: {self.rat[:20]}')
        # print(
        #     f'res station: { [f"{rs.op}, {rs.dest_tag}, {rs.tag1}, {rs.tag2}, {rs.val1}, {rs.val2}" for rs in filter(None, self.rs.entries[:6])] }'
        # )
        # # print(f'exec queue: { [f"{rs.op}, {rs.dest_tag}, {rs.tag1}, {rs.tag2}, {rs.val1}, {rs.val2}" for rs in filter(None, self.eq[:6])] }')
        # print(f'writeback queue: {self.wbq}')
        # print(f'memory: {self.mem}')