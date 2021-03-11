from processor import Processor
from instruction import Instruction


class SimpleProcessor(Processor):
    def __init__(
        self,
        program,
        symbols,
        prediction_method=None,
        instructions_per_cycle=1,
        debug=False,
    ):
        super().__init__(program, symbols, debug)

        self.RF = [0] * 32

    def cycle(self):
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

            if i.opcode == "lw":
                return self.MEM[i.target_address]
            elif i.opcode == "sw":
                self.MEM[i.target_address] = self.RF[i.target_register]
                self.executed += 1

            else:
                raise RuntimeError("Error handling a memory operation")

        def write_back(self, i):
            self.RF[i.target_register] = i.result
            self.executed += 1

        self.cycles += 1

        # Fetch
        blank_instruction = fetch(self)

        # Decode
        decoded_instruction = decode(self, blank_instruction)

        if decoded_instruction.branch_target:
            # set the pc accordingly and exit this cycle because no work is left to be performed on this instruction
            if decoded_instruction.branch_target != -1:
                self.PC = decoded_instruction.branch_target
            self.executed += 1
            return

        # Execute
        computed_instruction = decoded_instruction.compute()

        # Mem acess
        if computed_instruction.target_address is not None:
            result = mem_access(self, computed_instruction)
            computed_instruction.result = result

        # Writeback
        if computed_instruction.result is not None:
            write_back(self, computed_instruction)

    def print_stats(self):
        print(self.cycles)
        print(self.RF)
        print(self.MEM)
