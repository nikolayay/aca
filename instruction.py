import re

arithmetic = ["add", "sub", "mul", "mod", "div", "imul", "idiv"]
immediate = ["addi"]
memory = ["lw", "sw"]
branches = ["beq", "bne", "blt", "ble"]
jumps = ["j"]

colours = [
    "red",
    "yellow",
    "blue",
    "magenta",
    "bright_red",
    "bright_yellow",
    "bright_blue",
    "bright_magenta",
]


class Instruction:
    def __str__(self):
        return self.instruction_string

    def __init__(self, instruction_string, symbols, PC):

        self.symbols = symbols
        self.instruction_string = instruction_string

        self.opcode = None
        self.operand_str = None

        # fields that may be computed during execution
        self.target_address = None  # for loads/stores
        self.result = None  # for arithmetic
        self.branch_target = None  # for brnaches
        self.finished = False

        self.source_registers = []
        self.target_register = None
        self.immediate = None

        # colour tag for debugging
        self.colour = colours[PC % len(colours)]

    def parse(self):
        self.opcode = self.instruction_string.split()[0]
        self.operand_str = self.instruction_string.split(self.opcode)[1].strip()

        return self

    def collect_operands(self):
        source_registers = []

        # tag the registers with their respective roles
        if self.opcode in arithmetic:

            self.operands = self.parse_operands(
                "^(?P<rd>\$\w*) (?P<rs>\$\w*) (?P<rt>\$\w*)$"
            )

        elif self.opcode in immediate:

            self.operands = self.parse_operands(
                "^(?P<rt>\$\w*) (?P<rs>\$\w*) (?P<imm>-*\d+)$"
            )

        elif self.opcode in memory:

            self.operands = self.parse_operands(
                "^(?P<rt>\$\w*) *(?P<imm>\w+)\((?P<rs>\$\w*|\d*)\)$"
            )

        elif self.opcode in branches:

            self.operands = self.parse_operands(
                "^(?P<rs>\$\w*) (?P<rt>\$\w*) (?P<imm>-*\d+|\$*\w*)$"
            )

        elif self.opcode in jumps:

            # ! no source reg to worry about
            self.operands = self.parse_operands("^(?P<imm>\w*)$")

        else:
            raise RuntimeError(
                f"Collecting operands of {self.opcode} {self.operand_str} -> Not implemented"
            )

        return self

    def parse_operands(self, pattern):
        match = re.match(pattern, self.operand_str)
        if not match:
            raise RuntimeError(
                f"Match broken for instruction {self.opcode} {self.operand_str}"
            )

        operands = {}

        for k, v in match.groupdict().items():
            if v in self.symbols:
                operands[k] = self.symbols[v]
            elif v[0] == "$":
                operands[k] = int(v[1:])
            else:
                operands[k] = int(v)

        return operands

    def fetch_source_registers(self):
        source_registers = []

        # tag the registers with their respective roles
        if self.opcode in arithmetic:

            self.operands = self.parse_operands(
                "^(?P<rd>\$\w*) (?P<rs>\$\w*) (?P<rt>\$\w*)$"
            )

            source_registers.append(self.operands["rs"])
            source_registers.append(self.operands["rt"])

        elif self.opcode in immediate:

            self.operands = self.parse_operands(
                "^(?P<rt>\$\w*) (?P<rs>\$\w*) (?P<imm>-*\d+)$"
            )

            source_registers.append(self.operands["rs"])

        elif self.opcode in memory:

            self.operands = self.parse_operands(
                "^(?P<rt>\$\w*) *(?P<imm>\w+)\((?P<rs>\$\w*|\d*)\)$"
            )

            source_registers.append(self.operands["rs"])

        elif self.opcode in branches:

            self.operands = self.parse_operands(
                "^(?P<rs>\$\w*) (?P<rt>\$\w*) (?P<imm>-*\d+|\$*\w*)$"
            )

            source_registers.append(self.operands["rs"])
            source_registers.append(self.operands["rt"])

        elif self.opcode in jumps:

            # ! no source reg to worry about
            self.operands = self.parse_operands("^(?P<imm>\w*)$")

        elif self.opcode == "STALL":
            pass

        else:
            raise RuntimeError(
                f"Fetching source registers of {self.opcode} {self.operand_str} -> Not implemented"
            )

        return source_registers

    def read_register_file(self, RF):
        # tag the registers with their respective roles
        if self.opcode in arithmetic:

            # prefetching
            self.target_register = self.operands["rd"]
            self.rs = RF[self.operands["rs"]]
            self.rt = RF[self.operands["rt"]]

        elif self.opcode in immediate:

            # prefetching
            self.target_register = self.operands["rt"]
            self.rs = RF[self.operands["rs"]]
            self.imm = self.operands["imm"]

        elif self.opcode in memory:

            # prefetching
            self.target_register = self.operands["rt"]
            self.rs = RF[self.operands["rs"]]
            self.imm = self.operands["imm"]

        elif self.opcode in branches:

            # prefetching
            self.rs = RF[self.operands["rs"]]
            self.rt = RF[self.operands["rt"]]
            self.imm = self.operands["imm"]

            self.evaluate_branch_condition()

        elif self.opcode in jumps:

            # prefetching
            self.imm = self.operands["imm"]

            self.evaluate_branch_condition()

        elif self.opcode == "STALL":
            pass

        else:
            raise RuntimeError(
                f"Reading register file for {self.opcode} {self.operand_str} -> Not implemented"
            )

        return self

    """
    If the branch condition evaluated to true we set a branch target
    Otherise, set the special value -1     
    """

    def evaluate_branch_condition(self):
        if self.opcode not in branches + jumps:
            raise RuntimeError(
                f"You should not be calling this method when processing the instruction {self.opcode} {self.operand_str}"
            )

        if self.opcode == "beq":
            if self.rs == self.rt:
                self.branch_target = self.imm
            else:
                self.branch_target = -1

        elif self.opcode == "blt":
            if self.rs < self.rt:
                self.branch_target = self.imm
            else:
                self.branch_target = -1

        elif self.opcode == "ble":
            if self.rs <= self.rt:
                self.branch_target = self.imm
            else:
                self.branch_target = -1

        elif self.opcode == "j":
            self.branch_target = self.imm

        else:
            raise RuntimeError(f"Branch evaluate of {self.opcode} -> Not implemented")

    def compute(self):
        if self.opcode in branches + jumps:
            # if we hit a jump we try to evaluate the branch target
            # self.evaluate_registers()

            raise RuntimeError(
                "You should not call execute on branch or jump instructions"
            )

        if self.opcode == "add":
            self.result = self.rs + self.rt

        elif self.opcode == "sub":
            self.result = self.rs - self.rt

        elif self.opcode == "mul":
            self.result = self.rs * self.rt

        elif self.opcode == "imul":
            self.result = int(int(self.rs) * int(self.rt))

        elif self.opcode == "mod":
            self.result = int(int(self.rs) % int(self.rt))

        elif self.opcode == "div":
            self.result = self.rs / self.rt

        elif self.opcode == "idiv":
            self.result = int(int(self.rs) / int(self.rt))

        elif self.opcode == "addi":
            self.result = self.rs + self.imm

        elif self.opcode == "lw" or self.opcode == "sw":
            self.target_address = self.rs + self.imm

        elif self.opcode == "STALL":
            return self

        else:
            raise RuntimeError(f"Compute of {self.opcode} -> Not implemented")

        assert (self.result is not None) ^ (self.target_address is not None)

        return self


class Stall(Instruction):
    def __str__(self):
        return "STALL"

    def __init__(self):

        # self.symbols = symbols
        # self.instruction_string = instruction_string

        # self.opcode = None
        # self.operand_str = None

        # fields that may be computed during execution
        self.target_address = None  # for loads/stores
        self.result = None  # for arithmetic
        self.branch_target = None  # for brnaches
        # self.finished = False

        # self.source_registers = []
        self.target_register = None
        # self.immediate = None

        # colour tag for debugging
        self.colour = "black"
        self.finished = False
        self.opcode = "STALL"

        self.instruction_string = "STALL"
