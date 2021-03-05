from processor import Processor
from instruction import Instruction


class PipelinedProcessor(Processor):
    def __init__(self, program, symbols, debug=False):
        super().__init__(program, symbols, debug)

    def cycle(self):
        self.cycles += 1

        update_IF = self.IF.run(
            PC=self.PC, instruction_queue=self.instruction_queue)

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
                update_IF = self.IF.run(
                    PC=pc, instruction_queue=self.instruction_queue)
                # do not duplicate the PC update
                update_ID = update_ID[:-1]

        update_EX = self.EX.run(
            execution_queue=self.execution_queue,
            memory_queue=self.memory_queue,
            writeback_queue=self.writeback_queue,
        )

        update_MEM = self._MEM.run(
            MEM=self.MEM, memory_queue=self.memory_queue)

        update_WB = self.WB.run(
            RF=self.RF, writeback_queue=self.writeback_queue)

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
