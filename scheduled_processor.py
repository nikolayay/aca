import re
from typing import *
from processor import Processor
from columnar import columnar # type: ignore

class Instruction:
    def __str__(self):
        if self.opcode in ['lw', 'sw']: 
            if self.opcode == 'lw': return f'{self.opcode}, loading from $r{self.target_register} to address $r{self.source_reg1} + {self.immediate}'
            elif self.opcode == 'sw': return f'{self.opcode}, storing what is in ${self.source_reg1} from address $r{self.source_reg2} + {self.immediate}'
            else: raise RuntimeError("IDK HOW TO PRINT STORES EHEHEH")
        else: return f"{self.opcode}, {self.target_register} <- {self.source_reg1} op {self.source_reg2}/{self.immediate}"

    def __print__(self):
        return str(self.opcode)

    def __init__(self, opcode, target_register, source_reg1, source_reg2, immediate, fetched_at_pc):
        self.opcode = opcode
        self.target_register = target_register
        self.source_reg1 = source_reg1
        self.source_reg2 = source_reg2
        self.immediate = immediate
        self.fetched_at_pc = fetched_at_pc


    def writes_regs(self):
        if self.is_store(): return False
        elif self.is_branch(): return False
        else: return True

    def is_mem(self):
        return self.opcode in ['lw', 'sw']

    def is_branch(self):
        return self.opcode in ['beq', 'bne', 'blt', 'ble', 'j']

    def is_jump(self):
        return self.opcode == 'j'

    def is_store(self):
        return self.opcode == 'sw'



class ReorderBufferEntry:

    def __str__(self):
        return f"ROB Entry for op: {self.opcode}, dest: {self.destination}, val:{'Not ready' if self.value is None else self.value}"

    def __print__(self):
        return str(self)

    def __init__(self, opcode, destination, value, fetched_at_pc, done=False):
        self.opcode = opcode
        self.destination = destination # which architectural register we write to
        self.value = value             # if branch then this is the result of comparison
        self.fetched_at_pc = fetched_at_pc
        self.pc = None                 # the place in the program from where we should fetch the next instruction
        self.done = done
        # self.dispatched = False
        # self.allowed = 1
        # self.counter = 0

        self.id = None

class ReorderBuffer:

    def __str__(self):
        data = []
        header = ['commit pointer', 'id', 'operation', 'destination register', 'value', 'pc', 'done']
        sslice = self.entries[:18] if self.commit_pointer < 9 else self.entries[self.commit_pointer - 3 : self.commit_pointer + 9]

        for i, e in enumerate(sslice):

            if e is None: data.append(['empty'] * len(header))
            else: 
                pointer = '->' if e.id == self.commit_pointer else ''
                data.append([pointer, e.id, e.opcode, e.destination, e.value, e.pc, e.done])

        rob_table = columnar(data, header, no_borders=True)

        return f'REORDER BUFFER\n{rob_table}'


    def __init__(self):
        self.entries = [None] * 32 # equal to number of registers

        self.commit_pointer = 0
        self.issue_pointer = 0

    def lookup(self, ix):
        return self.entries[ix]

    def is_available(self):
        return True
        occupied = len([e for e in self.entries if e is not None and e.destination])
        return occupied < len(self.entries) 

    def add(self, instruction: Instruction, pc:int) -> Tuple[ReorderBufferEntry, int]:
        
        destination = 32 if instruction.is_store() or instruction.is_branch() else instruction.target_register # dummy value if needed


        entry = ReorderBufferEntry(opcode=instruction.opcode, 
                                    destination=destination, 
                                    value=None, 
                                    fetched_at_pc = instruction.fetched_at_pc,
                                    done=False)
                                    
        # note down the next pc we should fetch after this instruction
        if instruction.is_branch(): entry.pc = instruction.immediate
        else: entry.pc = instruction.fetched_at_pc + 1

        entry.id = self.issue_pointer
        self.entries[self.issue_pointer] = entry

        # print(f'added {entry} at index {self.issue_pointer}')

        entry_pointer = self.issue_pointer

        self.issue_pointer += 1

        if self.issue_pointer == len(self.entries):
            self.issue_pointer = 0
        
        return entry, entry_pointer

    # mark instruction as having finished execution
    def done(self, ix, value):
        rob_entry = self.entries[ix]
        rob_entry.value = value
        rob_entry.done = True


    def can_commit(self):
        first = self.entries[self.commit_pointer]

        if first is None: return False

        return first.done

    """
    Free up the space at commit pointer and incrememnt
    """
    def free(self):

        # self.entries[self.commit_pointer] = None


        self.commit_pointer += 1
        
        if self.commit_pointer == len(self.entries):
            self.commit_pointer = 0


class RegisterFile:
    def __init__(self):
        self.ARF = [0] * 33 # architectural registers + extra for the ROB
        self.RAT = [None] * 33 # mappings to architectural registers # if none we just return corresponding ARF, else its always a ROB mapping

    """
    Only used by store instructions
    """
    def read_for_mem_access(self, register_ix):
        return self.ARF[register_ix]
    
    
    def read(self, register_ix:int, ROB: ReorderBuffer):
        
        # no mapping
        if self.RAT[register_ix] == None:
            return None, self.ARF[register_ix]
        else:
          
            rob_index = self.RAT[register_ix]
            rob_entry = ROB.lookup(rob_index)
            # we return the rob tag and no value
            if rob_entry.done: 
                return None, rob_entry.value
            else:
                return rob_index, None
    
    def write(self, register_ix, value):
        self.ARF[register_ix] = value

    def remap(self, target_register:int, rob_entry_pointer: int):
        self.RAT[target_register] = rob_entry_pointer

    def commit(self, rob_entry: ReorderBufferEntry, rob_commit_pointer: int):
        if not rob_entry.done: raise ValueError("BAD ROB Entry")
       
        self.write(rob_entry.destination, rob_entry.value)

        # remove mapping if RAT points at the entry we are committing
        if self.RAT[rob_entry.destination] == rob_commit_pointer:
            self.RAT[rob_entry.destination] = None
                
    def read_registers(self, instruction: Instruction, ROB: ReorderBuffer):

       
        s1 = instruction.source_reg1
        s2 = instruction.source_reg2

        t1, v1 = self.read(s1, ROB) # get either a tag or a value


        if s2 is None:
            if instruction.is_branch(): raise RuntimeError('this is fucked')
            return (t1, None, v1, instruction.immediate)

        else:
            t2, v2 = self.read(s2, ROB)
            return (t1, t2, v1, v2)

    def reset_mappings(self):
        self.RAT = [None] * 33

   


class LoadStoreQueueEntry:
    def __str__(self):
        return f"LSQ Entry for op: {self.opcode}, target_address: {self.target_address}, rob_pointer: {self.dest_tag}"

    def __print__(self):
        return str(self)

    def __init__(self, opcode, dest_tag, target_address, offset, tag_base, base, tag_value, value):
        self.opcode = opcode

        self.dest_tag = dest_tag # the rob tag for the respective instruction to broadcast upon completion
        
        self.target_address = target_address # value + immediate
        self.offset = offset
        self.tag_base = tag_base
        self.base = base

        self.tag_value = tag_value # the register from which we store or its tag
        self.value = value         # the value to store/load

        # metadata
        self.dispatched = False
        self.id = None
        

    def is_ready(self, queue):
        # load is ready if there are no previous stores in the queue with the same address
        # or if
        if self.opcode == 'lw':
           
            # see if there is any previous stores with a matching address
            prev_stores = [e for e in queue[:self.id]
                            if e is not None and e.target_address == self.target_address and e.opcode == 'sw']
            
            # if there are no previous stores we need to hit the memory if we have an address
            if not prev_stores:
                return self.target_address is not None and not self.dispatched
            
            # todo otherwise we wait for an address to be forwarded to us
            else:
                return self.target_address is not None and not self.dispatched and self.value is not None

        # store is ready when it has an address and a value to put into that address
        elif self.opcode == 'sw': 
            return self.target_address is not None and not self.dispatched and self.value is not None
        
        else: raise RuntimeError('oh god!')
       
        

"""
Integrates and address unit
"""
class LoadStoreQueue():

    def __str__(self):
        data = []
        header = ['commit pointer', 'id' ,'operation', 'ROB tag', 
                 'target address', 'offset', 
                 'base tag',
                 'base',
                 'source tag', 
                 'source value', 
                 'ready to dispatch in next cycle?', 
                 'dispatched']
        
        sslice = self.entries[:6] if self.commit_pointer < 3 else self.entries[self.commit_pointer - 3 : self.commit_pointer + 3]
        
        for i, e in enumerate(sslice):


            if e is None: data.append( ['x'] + (['empty'] * 11))
            else: 
                pointer = '->' if e.id == self.commit_pointer else ''
                data.append([pointer, e.id, e.opcode, e.dest_tag, e.target_address, e.offset, e.tag_base, e.base, e.tag_value, e.value, e.is_ready(self.entries), e.dispatched])

        lsq_table = columnar(data, header, no_borders=True)

        return f'LOAD STORE QUEUE\n{lsq_table}'

    def __init__(self):
        self.entries = [None] * 32
        self.commit_pointer = 0
        self.issue_pointer = 0

   
    # performs load store forwarding
    def forward_store(self, lsq_entry_to_commit: LoadStoreQueueEntry, value):
        next_entries = [e for e in self.entries[lsq_entry_to_commit.id:] if e is not None and e.opcode == 'lw']
        
        for e in next_entries:
            if e.target_address == lsq_entry_to_commit.target_address:
                e.value = value

    
    """
    This can hydrate the base and produce a target address or a value for the store instruction
    """
    def capture(self, tag, value):
        # iterate over the entries, check both tags and set the correspoding value, while unsetting the tag
        for e in [e for e in self.entries if e is not None]:
            if e.tag_base is not None and e.tag_value is not None and e.tag_base == e.tag_value: raise RuntimeError('Tags match, reimplement')
            
            if e.opcode == 'sw' and e.tag_value == tag:
                e.value = value
            if e.tag_base == tag: 
                e.target_address = value + e.offset


    def lookup(self, ix):
        return self.entries[ix]

    def add(self, instruction:Instruction, rob_pointer:int, RF: RegisterFile, ROB: ReorderBuffer):

        if instruction.opcode == 'lw':
            # try to compute address, NB this value is different from the return value from memory that we have in LSQ entry

            target_address = None
            offset = instruction.immediate
            
            tag_base, base = RF.read(instruction.source_reg1, ROB)

            if base is not None: target_address = base + offset
        
            entry = LoadStoreQueueEntry(opcode=instruction.opcode, 
                                        dest_tag=rob_pointer,
                                        target_address=target_address, 
                                        offset=offset, 
                                        tag_base=tag_base,
                                        base=base,
                                        tag_value=None,
                                        value=None)

        if instruction.opcode == 'sw':
            
            if instruction.target_register is not None and instruction.source_reg1 is None or instruction.source_reg2 is None: 
                raise RuntimeError('sw parsed incorrectly')

            offset = instruction.immediate
            target_address = None   # base + offset
            tag_base = None
            base = None # from source register
            tag_value = None     
            value = None     
            
            # try to compute the address
            tag_base, base = RF.read(instruction.source_reg2, ROB)
            if base is not None: target_address = base + offset

            # try to figure out the register
            tag_value, value = RF.read(instruction.source_reg1, ROB)
            

            entry = LoadStoreQueueEntry(opcode=instruction.opcode, 
                                        dest_tag=rob_pointer,
                                        target_address=target_address, 
                                        offset=offset, 
                                        tag_base=tag_base,
                                        base=base,
                                        tag_value=tag_value,
                                        value=value)

    
        entry.id = self.issue_pointer
        self.entries[self.issue_pointer] = entry
        entry_pointer = self.issue_pointer
        
        self.issue_pointer += 1

        if self.issue_pointer == len(self.entries):
            self.issue_pointer = 0

        return entry

    # sometimes loads are added to the queue after the stores have comitted. we need to try to hydrate every store on the queue
    def hydrate_loads(self):
        # for every uncommitted load, call hydrate with preious store
        loads = [e for e in self.entries if e is not None and e.opcode == 'lw' and e.id >= self.commit_pointer]

        for load in loads:
            prev_stores = [e for e in self.entries[: load.id] if e is not None and e.opcode == 'sw']
            
            if prev_stores:
                for store in prev_stores:
                    if load.target_address == store.target_address:
                        load.value = store.value

            #self.forward_store(load, load.value)



    def get_next_ready(self):
        self.hydrate_loads()

        ready_entry_ixs = [i for i, e in enumerate(self.entries) if e is not None and e.is_ready(self.entries)]

        if not ready_entry_ixs: return None

        ix = ready_entry_ixs[0]
        first = self.entries[ix]

        # # free the station
        # self.entries[ix] = None
        # print(self.entries)

        self.entries[ix].dispatched = True


        return first

    def free(self):

        # self.entries[self.commit_pointer] = None

        self.commit_pointer += 1
        
        if self.commit_pointer == len(self.entries):
            self.commit_pointer = 0




class ReservationStationEntry:

    def __str__(self):
        return f"RS Entry for op: {self.opcode}, rob_tag: {self.dest_tag}, tag1: {self.tag1}, tag2: {self.tag2}, val1: {self.val1}, val2: {self.val2}"

    def __print__(self):
        return str(self)

    def __init__(self, opcode, dest_tag, tag1, tag2, val1, val2):
        self.opcode = opcode
        self.dest_tag = dest_tag # the rob tag for the respective instruction to broadcast upon completion
        
        self.tag1 = tag1 # this is where in the ROB we can get the value of source reg 1 once its ready
        self.tag2 = tag2 # this is where in the ROB we can get the value of source reg 2 OR immediate once its ready
        
        self.val1 = val1 # source reg 1 
        self.val2 = val2 # source reg 2 OR immediate
        
        # self.dispatched = False
        # self.allowed = 1
        # self.counter = 0

    def is_ready(self):
        return self.val1 is not None and self.val2 is not None


class ReservationStation():

    def __str__(self):
        data = []
        header = ['opcode', 'rob_tag', 'operand tag 1', 'operand tag 2', 'operand value 1', 'operand value 2', 'ready to dispatch in next cycle?']
        
        for i, e in enumerate(self.entries[:6]):

            if e is None: data.append( ['empty'] * len(header))
            else: data.append([e.opcode, e.dest_tag, e.tag1, e.tag2, e.val1, e.val2, e.is_ready()])

        rs_table = columnar(data, header, no_borders=True)

        return f'RESERVATION STATION\n{rs_table}'

    def __init__(self):
        self.entries = [None] * 265

    def capture(self, tag, value):
        # iterate over the entries, check both tags and set the correspoding value, while unsetting the tag
        for e in [e for e in self.entries if e is not None]:
            if e.tag1 == tag: e.val1 = value
            if e.tag2 == tag: e.val2 = value


    def add(self, instruction:Instruction, rob_pointer:int, RF: RegisterFile, ROB: ReorderBuffer):
        
        # if instruction.is_branch():
        #     entry = ReservationStationEntry(
        #         instruction.opcode, rob_pointer, None, None, 0, 0)
        # else:
        if instruction.is_jump():
            entry = ReservationStationEntry(instruction.opcode, rob_pointer, None, None, 0, 0)
        else:
            t1, t2, v1, v2 = RF.read_registers(instruction, ROB)
            entry = ReservationStationEntry(instruction.opcode, rob_pointer, t1, t2, v1, v2)

        # loop over and look for empty slot
        if None in self.entries:
            ix = self.entries.index(None)
            self.entries[ix] =  entry

        return entry

    def get_next_ready(self):
        ready_entry_ixs = [i for i, e in enumerate(self.entries) if e is not None and e.is_ready()]

        if not ready_entry_ixs: return None

        ix = ready_entry_ixs[0]
        first = self.entries[ix]

        # free the station
        self.entries[ix] = None


        return first

   

class Predictor:
    def __init__(self, prediction_method:str):
        self.predicted_pc = None

        self.prediction_method = prediction_method
        self.predict = getattr(self, prediction_method)

        self.predicted = 0
        self.misses = 0

        self.btb: Dict[int,int] = {}


    def not_taken(self, pc):

        predicted_pc = pc + 1

        # record
        self.btb[pc] = predicted_pc

        return predicted_pc

    def taken(self, pc):
        raise RuntimeError('not implemented')

    def one_bit(self, pc):
        
        predicted_pc = pc + 1
        next_pc = self.btb[pc] if pc in self.btb else predicted_pc

        # print(f'predicting {next_pc} for instuction at pc {pc}')

        # record
        self.btb[pc] = next_pc

        return next_pc

    def two_bit(self, pc):
        raise RuntimeError('not implemented')


    def prediction_accuracy(self):
        if self.predicted == 0: return 1
        return 1 - (self.misses / self.predicted)

    
    # def kek(self, rob_entry: ReorderBufferEntry):
    #     print(rob_entry, self.predicted_pc)
    #     return rob_entry.pc == self.predicted_pc


    def check(self, rob_entry: ReorderBufferEntry):
        
        # if this is a branch we could have been wrong
        if Decoder.is_branch(rob_entry.opcode):

            self.predicted += 1


            # rob values for branches contain the boolean result of the branch condition
            taken = bool(rob_entry.value)


            if taken:
                correct_pc = rob_entry.pc
            else:
                correct_pc = rob_entry.fetched_at_pc + 1
            
            # have we made the correct prediction
            success = correct_pc == self.btb[rob_entry.fetched_at_pc]

            print(f'taken branch?: {taken}')
            print(f'prediction success {success}')
            print(rob_entry)

        

            if not success:
                self.misses += 1
                
                if self.prediction_method == 'one_bit':

                    # print(f'branch at pc: {rob_entry.fetched_at_pc}, predicted: {self.btb[rob_entry.fetched_at_pc]}, should have been: {correct_pc}')
                    self.btb[rob_entry.fetched_at_pc] = correct_pc

                    
                    

            # # if our brediction at that pc was wrong then record the miss 
            # # FIXME this is nonsense right now
            # if self.predicted_pc != correct_pc: self.misses += 1
            
            # we return the condition because of the default non taken scheme. we should return the result of the check
            return success, correct_pc
        
        # otherwise we are always predicting correctly
       
        return True, None


class Decoder:
    def __init__(self, symbols):
        self.symbols = symbols
    
    def decode(self, instruction_string: str, fetched_at_pc:int)-> Instruction:
        
        # separate opcode and operand string
        opcode = instruction_string.split()[0]
        operand_str = instruction_string.split(opcode)[1].strip()

        target_register, source_registers, immediate = self.fetch_register_names(opcode, operand_str)

        return Instruction(opcode, target_register, source_registers[0], source_registers[1], immediate, fetched_at_pc)


    def fetch_register_names(self, opcode, operand_str):
        target_register = None
        source_registers = [None] * 2
        immediate = None


        # tag the registers with their respective roles
        if opcode in ['add', 'sub', 'mul', 'mod', 'div', 'imul', 'idiv']:

            operands = self.parse_operands(operand_str, "^(?P<rd>\$\w*) (?P<rs>\$\w*) (?P<rt>\$\w*)$")

            target_register = operands['rd']
            source_registers[0] = operands['rs']
            source_registers[1] = operands['rt']

        elif opcode in ['addi']:
            
            operands = self.parse_operands(operand_str, "^(?P<rt>\$\w*) (?P<rs>\$\w*) (?P<imm>-*\d+)$")

            target_register = operands['rt']
            source_registers[0] = operands['rs']
            immediate = operands['imm']

        elif opcode in ['lw', 'sw']:

            operands = self.parse_operands(operand_str, "^(?P<rt>\$\w*) *(?P<imm>\w+)\((?P<rs>\$\w*|\d*)\)$")

            if opcode == 'lw':
                target_register = operands['rt']
                source_registers[0] = operands['rs']
                immediate = operands['imm']
            
            if opcode == 'sw':
                source_registers[0] = operands['rt']
                source_registers[1] = operands['rs']
                immediate = operands['imm']


        elif opcode in ['beq', 'bne', 'blt', 'ble']:

            operands = self.parse_operands(operand_str, "^(?P<rs>\$\w*) (?P<rt>\$\w*) (?P<imm>-*\d+|\$*\w*)$")
            source_registers[0] = operands['rs']
            source_registers[1] = operands['rt']
            immediate = operands['imm']

        elif opcode in ['j']:
            # ! no source reg to worry about
            operands = self.parse_operands(operand_str, "^(?P<imm>\w*)$")
            immediate = operands['imm']

        
        elif opcode == 'STALL':
            pass

        else:
            raise RuntimeError(
                f"Fetching source registers of {opcode} {operand_str} -> Not implemented")

        return target_register, source_registers, immediate


    def parse_operands(self, operand_str, pattern):


        match = re.match(pattern, operand_str)
        
        if not match:
            raise RuntimeError(
                f"Match broken for instruction {self.opcode} {operand_str}")

        operands = {}

        for k, v in match.groupdict().items():
            if v in self.symbols:
                operands[k] = self.symbols[v]
            elif v[0] == '$':
                operands[k] = int(v[1:])
            else:
                operands[k] = int(v)

        return operands

    @staticmethod
    def is_mem(opcode: str):
        return opcode in ['lw', 'sw']

    @staticmethod
    def is_branch(opcode: str):
        return opcode in ['beq', 'bne', 'blt', 'ble', 'j']
        

class ALU:

    def __init__(self):
        pass

    def execute(self, rs_entry: ReservationStationEntry):
        opcode = rs_entry.opcode

        result = None

        if opcode == 'add':
            result = rs_entry.val1 + rs_entry.val2

        elif opcode == 'sub':
            result = rs_entry.val1 - rs_entry.val2

        elif opcode == 'mul':
            result = rs_entry.val1 * rs_entry.val2

        elif opcode == 'imul':
            result = int(int(rs_entry.val1) * int(rs_entry.val2))

        elif opcode == 'mod':
            result = int(int(rs_entry.val1) % int(rs_entry.val2))

        elif opcode == 'div':
            result = rs_entry.val1 / rs_entry.val2

        elif opcode == 'idiv':
            result = int(int(rs_entry.val1) / int(rs_entry.val2))

        elif opcode == 'addi':
            result = rs_entry.val1 + rs_entry.val2

        elif opcode in ['beq', 'bne', 'blt', 'ble', 'j']:
            if opcode == 'blt':
                result = bool(rs_entry.val1 < rs_entry.val2)
                # raise RuntimeError(f'{opcode} not implementedddd')

            elif opcode == 'beq':
                result = bool(rs_entry.val1 == rs_entry.val2)

            elif opcode == 'ble':
                result = bool(rs_entry.val1 <= rs_entry.val2)
                # raise RuntimeError(f'{opcode} not implementedddd')

            elif opcode == 'j':
                result = True  # always taken
                
            else: raise RuntimeError(f'{opcode} not implemented')
            
           

        else:
            raise RuntimeError(f"You are not supposed to perform ALU operation on operation {opcode}")

        assert(result is not None)

        return result


class ScheduledProcessor(Processor):
    def __init__(self, program, symbols, prediction_method, instructions_per_cycle=1, debug=False):
        super().__init__(program, symbols, debug)

        self.RF = [0] * 33

        self.rf = RegisterFile()
        self.decoder = Decoder(symbols)
        self.predictor = Predictor(prediction_method)
        
        self.alu = ALU()

        self.decode_queue = []
        self.issue_queue = []
        self.execute_queue = []
        self.mem_queue = []

        self.writeback_queue = []

        self.rob = ReorderBuffer()
        self.rs  = ReservationStation()
        self.lsq = LoadStoreQueue()

        self.instructions_per_cycle = instructions_per_cycle

        self.debug=debug




    def tick(self, updates):
        for action, attr, val, in updates:

            # get the correct queue
            current = getattr(self, attr)

            if action == 'pop':
               
                updated = current[:-1]
                setattr(self, attr, updated)

            elif action == 'push':
                # print(f'pushing to {attr}')

                updated = [val] + current
                setattr(self, attr, updated)

            # this will get called every instruction fetch
            elif action == 'set':
                setattr(self, attr, val)

            else:
                raise RuntimeError(f'Update type {action} not implemented')
        
    

    def cycle(self):
        self.cycles += 1

        updates = []

        for _ in range(self.instructions_per_cycle):

            fetch_update     = self.fetch()

            decode_update    = self.decode()

            issue_update     = self.issue()

            dispatch_update  = self.dispatch()

            execute_update   = self.execute()

            mem_update       = self.mem()

            writeback_update, flushing_flag = self.writeback()

            # flushed the pipeline, update nothing
            if flushing_flag: return

            updates = fetch_update + decode_update + issue_update + dispatch_update + execute_update + mem_update + writeback_update

            self.tick(updates)
        
        self.RF = self.rf.ARF

        if self.debug:
            self.print_stats()
            txt = input("Press enter for next cycle")
        # print(self.RF)

        # raise RuntimeError("Not implemented")
        # if self.cycles == 8: self.rf.write(31, 1)

    """
        1. fetch the instruction string from the program
        2. increment the PC

    """
    def fetch(self):
        if self.PC >= len(self.program):
            return []

        if (self.PC > len(self.program) or self.PC < 0): raise RuntimeError( f"PC out of bounds. PC={self.PC} for program of length {len(self.program)}")
        
        instruction_string = self.program[self.PC]
        predicted_pc = self.predictor.predict(self.PC)

        return [('push', 'decode_queue', (instruction_string, self.PC)), ('set', 'PC', predicted_pc)]

    def decode(self):
        
        updates = []
        
        if (len(self.decode_queue) > 0):
           
            # parse the instruction string, compose and return an instance of the instruction class with the fields
            instruction_string, fetched_at_pc = self.decode_queue[-1]
            updates += [('pop', 'decode_queue', None)]


            # note down the predicted pc
            instruction = self.decoder.decode(instruction_string, fetched_at_pc)

            updates += [('push', 'issue_queue', instruction)]
        
        return updates

    def issue(self):
        updates = []
        

        # if we have an available ROB and available RS entry
        if (len(self.issue_queue) > 0) and self.rob.is_available():
           
            # parse the instruction string, compose and return an instance of the instruction class with the fields
            instruction = self.issue_queue[-1]
            updates += [('pop', 'issue_queue', None)]

            # add to rob
            rob_entry, rob_entry_pointer = self.rob.add(instruction, self.PC)
            # add to reservation station
            if instruction.is_mem():
                lsq_entry = self.lsq.add(instruction, rob_entry_pointer, self.rf, self.rob)
            else:
                rs_entry = self.rs.add(instruction, rob_entry_pointer, self.rf, self.rob)


            # rename accordingly
            if instruction.writes_regs():
                self.rf.remap(instruction.target_register, rob_entry_pointer)

        return updates


    def dispatch(self):
        updates = []
        # find instruction to dispatch from RS
        rs_entry = self.rs.get_next_ready()
        lsq_entry = self.lsq.get_next_ready()

        if rs_entry:
            updates += [('push', 'execute_queue', rs_entry)]

        if lsq_entry:
            updates += [('push', 'mem_queue', lsq_entry)]

            
        # go over both RS and LSQ and return any ready values, free up the space accordingly
        # ready values are those with both value fields available 
        return updates

    def execute(self):
        updates = []
        if len(self.execute_queue) > 0:


            rs_entry = self.execute_queue[-1]
            updates += [('pop', 'execute_queue', None)]

            rob_tag = rs_entry.dest_tag
            
            result = self.alu.execute(rs_entry)
            updates += [('push', 'writeback_queue', (rob_tag, result))]

        return updates


    def mem(self):

        updates = []
        if len(self.mem_queue) > 0:

            lsq_entry = self.mem_queue[-1]
            updates += [('pop', 'mem_queue', None)]

            rob_tag = lsq_entry.dest_tag

            if lsq_entry.opcode == 'lw':
                
                # hit memory if we have to
                if lsq_entry.value is None:
                    # loading 
                    # fetching outside of memory due to branch misprediction, ignore this because we flush in a couple of cycles
                    if lsq_entry.target_address >= len(self.MEM):
                        result = -30
                    else:
                        result = self.MEM[lsq_entry.target_address]
                    
                    updates += [('push', 'writeback_queue', (rob_tag, result))]
                
                # or we just pass the value straight up
                else:
                    updates += [('push', 'writeback_queue', (rob_tag, lsq_entry.value))]


                    



            elif lsq_entry.opcode == 'sw':

                updates += [('push', 'writeback_queue', (rob_tag, lsq_entry.value))]
            
            else: raise ValueError("Something is really wrong with the mem component")


        return updates


    def writeback(self):
        updates = []
        
        if len(self.writeback_queue) > 0:
        
            # update the rob and boradcast

            rob_tag, result = self.writeback_queue[-1]
            updates += [('pop', 'writeback_queue', None)]
            
            # 1. broadcast the finished value to the reservation station and lsq
            if result is not None: self.broadcast(rob_tag, result)

            # mark rob entry as done and hydrate the value
            self.rob.done(rob_tag, result)


        if self.rob.can_commit():
            
            rob_entry_to_commit = self.rob.lookup(self.rob.commit_pointer)

            # checking the branch predictor
            success, correct_pc = self.predictor.check(rob_entry_to_commit)

            if not success:
                print("FLUSHING")
                self.flush_pipeline(pc=correct_pc)
                return [], True


            # committing memory operations
            if Decoder.is_mem(rob_entry_to_commit.opcode):
                
                lsq_entry_to_commit = self.lsq.lookup(self.lsq.commit_pointer)
                
                # stores get put to writeback queue in mem cycle
                if rob_entry_to_commit.opcode == 'sw':
                    # perform the store
                    self.MEM[lsq_entry_to_commit.target_address] = rob_entry_to_commit.value
                    
                    # notify all the loads with matching address of the value, this allows them to dispatch
                    self.lsq.forward_store(lsq_entry_to_commit, rob_entry_to_commit.value)

                self.lsq.free()

            

            # committing everything else
            self.rf.commit(rob_entry_to_commit, self.rob.commit_pointer)

            # free the rob entry and increment commit pointer
            self.rob.free()

            self.executed += 1
            

        return updates, False


    def broadcast(self, tag, value):
        # call the capture methods of the queues
        self.rs.capture(tag, value)
        self.lsq.capture(tag, value)

        

    def running(self):
        v = self.rf.ARF[31]

        return v != 1

    def flush_pipeline(self, pc):
        # reset everything
        self.rf.reset_mappings()
        self.decode_queue = []
        self.issue_queue = []
        self.execute_queue = []
        self.mem_queue = []

        self.writeback_queue = []

        self.rob = ReorderBuffer()
        self.rs = ReservationStation()
        self.lsq = LoadStoreQueue()


        # set the pc
        self.PC = pc

        # increment executed to count the branch
        self.executed += 1


    def print_stats(self):
        print(f'CYCLE: {self.cycles}')
        print(self.RF)
        print(self.MEM)

        print(f'ROB COMMIT POINTER -> {self.rob.commit_pointer}')
        print(self.rob)
        print(self.rs)

        print(f'LSQ COMMIT POINTER -> {self.lsq.commit_pointer}')
        print(self.lsq)

        print(self.rf)




        print({i:line for i, line in enumerate(self.program)})
