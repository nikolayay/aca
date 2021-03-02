import re

arithmetic = ['add', 'sub', 'mul', 'mod', 'div', 'imul', 'idiv']
immediate = ['addi']
memory = ['lw', 'sw']
branches = ['beq', 'bne', 'blt', 'ble']
jumps = ['j']

class Instruction:

    def __str__(self):
        return f'{self.opcode} {self.operand_str}'
    def __init__(self, opcode, operand_str, RF, symbols):
        self.opcode = opcode
        self.operand_str = operand_str
        self.symbols = symbols
        self.branch_target = None

        if self.opcode in arithmetic:

            operands = self.parse_operands(
                "^(?P<rd>\$\w*) (?P<rs>\$\w*) (?P<rt>\$\w*)$")

            # prefetching
            self.target = operands['rd']
            self.rs = RF[operands['rs']]
            self.rt = RF[operands['rt']]

        elif self.opcode in immediate:

            operands = self.parse_operands(
                "^(?P<rt>\$\w*) (?P<rs>\$\w*) (?P<imm>-*\d+)$")

            # prefetching
            self.target = operands['rt']
            self.rs = RF[operands['rs']]
            self.imm = operands['imm']

        elif self.opcode in memory:

            operands = self.parse_operands(
                "^(?P<rt>\$\w*) *(?P<imm>\w+)\((?P<rs>\$\w*|\d*)\)$")

            # prefetching
            self.target = operands['rt']
            self.rs = RF[operands['rs']]
            self.imm = operands['imm']

        elif self.opcode in branches:

            operands = self.parse_operands(
                "^(?P<rs>\$\w*) (?P<rt>\$\w*) (?P<imm>-*\d+|\$*\w*)$")

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

        else:
            raise RuntimeError(
                f"Decode of {self.opcode} {self.operand_str} -> Not implemented")

    def parse_operands(self, pattern):
        match = re.match(pattern, self.operand_str)
        if not match:
            raise RuntimeError(
                f"Match broken for instruction {self.opcode} {self.operand_str}")

        operands = {}

        for k, v in match.groupdict().items():
            if v in self.symbols:
                operands[k] = self.symbols[v]
            elif v[0] == '$':
                operands[k] = int(v[1:])
            else:
                operands[k] = int(v)

        return operands

    """
    If the branch condition evaluated to true we set a branch target
    Otherise, set the special value -1     
    """

    def evaluate_registers(self):
        if self.opcode not in branches + jumps:
            raise RuntimeError(
                f"You should not be calling this method when processing the instruction {self.opcode} {self.operand_str}")

        if self.opcode == 'beq':
            if (self.rs == self.rt):
                self.branch_target = self.imm
            else:
                self.branch_target = -1

        elif self.opcode == 'blt':
            if (self.rs < self.rt):
                self.branch_target = self.imm
            else:
                self.branch_target = -1

        elif self.opcode == 'ble':
            if (self.rs <= self.rt):
                self.branch_target = self.imm
            else:
                self.branch_target = -1

        elif self.opcode == 'j':
            self.branch_target = self.imm

        else:
            raise RuntimeError(
                f"Branch evaluate of {self.opcode} -> Not implemented")

    # returns a target_address and the result and a branch target
    def execute(self):
        if self.opcode in branches + jumps:
            # if we hit a jump we try to evaluate the branch target 
            # self.evaluate_registers()
            
            raise RuntimeError(
                "You should not call execute on branch or jump instructions")

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
