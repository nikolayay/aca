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

    def __init__(self, opcode, target_register, source_reg1, source_reg2, immediate):
        self.opcode = opcode
        self.target_register = target_register
        self.source_reg1 = source_reg1
        self.source_reg2 = source_reg2
        self.immediate = immediate


    def is_mem(self):
        return self.opcode in ['lw', 'sw']

    def is_store(self):
        return self.opcode == 'sw'



class ReorderBufferEntry:

    def __str__(self):
        return f"ROB Entry for op: {self.opcode}, dest: {self.destination}, val:{'Not ready' if self.value is False else self.value}"

    def __print__(self):
        return str(self)

    def __init__(self, opcode, destination, value, done=False):
        self.opcode = opcode
        self.destination = destination # which architectural register we write to
        self.value = value             # if branch then this is the value we get
        self.done = done
        # self.dispatched = False
        # self.allowed = 1
        # self.counter = 0

        self.id = None

class ReorderBuffer:

    def __str__(self):
        data = []
        header = ['commit pointer', 'id', 'operation', 'destination register', 'value', 'done']
        sslice = self.entries[:6] if self.commit_pointer < 3 else self.entries[self.commit_pointer - 3 : self.commit_pointer + 3]

        for i, e in enumerate(sslice):

            if e is None: data.append(['empty'] * len(header))
            else: 
                pointer = '->' if e.id == self.commit_pointer else ''
                data.append([pointer, e.id, e.opcode, e.destination, e.value, e.done])

        rob_table = columnar(data, header, no_borders=True)

        return f'REORDER BUFFER\n{rob_table}'


    def __init__(self):
        self.entries = [None] * 32 # equal to number of registers

        self.commit_pointer = 0
        self.issue_pointer = 0

    def lookup(self, ix):
        return self.entries[ix]

    def is_available(self):
        occupied = len([e for e in self.entries if e and e.destination])
        return occupied < len(self.entries) - 1

    def add(self, instruction: Instruction) -> Tuple[ReorderBufferEntry, int]:
        
        destination = 32 if instruction.is_store() else instruction.target_register

        entry = ReorderBufferEntry(opcode=instruction.opcode, 
                                   destination=destination, 
                                   value=None, 
                                   done=False)

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

        if not first: return False

        return first.done

    """
    Free up the space at commit pointer and incrememnt
    """
    def free(self):

        #self.entries[self.commit_pointer] = None


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

        if not s2:
            return (t1, None, v1, instruction.immediate)

        else:
            t2, v2 = self.read(s2, ROB)
            return (t1, t2, v1, v2)


   


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

        # for stores only
        self.tag_value = tag_value # the register from which we store or its tag
        self.value = value

        # metadata
        self.dispatched = False
        self.id = None
        

    def is_ready(self):
        if self.opcode == 'lw': return self.target_address is not None and not self.dispatched
        elif self.opcode == 'sw': return self.target_address is not None and not self.dispatched and self.value is not None
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
                data.append([pointer, e.id, e.opcode, e.dest_tag, e.target_address, e.offset, e.tag_base, e.base, e.tag_value, e.value, e.is_ready(), e.dispatched])

        lsq_table = columnar(data, header, no_borders=True)

        return f'LOAD STORE QUEUE\n{lsq_table}'




    def __init__(self):
        self.entries = [None] * 32
        self.commit_pointer = 0
        self.issue_pointer = 0

    
    """
    This can hydrate the base and produce a target address or a value for the store instruction
    """
    def capture(self, tag, value):
        # iterate over the entries, check both tags and set the correspoding value, while unsetting the tag
        for e in [e for e in self.entries if e is not None]:
            if e.tag_base == tag: 
                e.target_address = value + e.offset

            if e.opcode == 'sw' and e.tag_value == tag:
                e.value = value


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
            print(instruction)
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


    def get_next_ready(self):
        ready_entry_ixs = [i for i, e in enumerate(self.entries) if e is not None and e.is_ready()]

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
        return f"RS Entry for op: {self.opcode}, rob_tag: {self.dest_tag},2: {self.tag1}, tag2: {self.tag2}, val1: {self.val1}, val2: {self.val2}"

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

   

class Decoder:
    def __init__(self, symbols):
        self.symbols = symbols
    
    def decode(self, instruction_string: str)-> Instruction:
        
        # separate opcode and operand string
        opcode = instruction_string.split()[0]
        operand_str = instruction_string.split(opcode)[1].strip()

        target_register, source_registers, immediate = self.fetch_register_names(opcode, operand_str)

        return Instruction(opcode, target_register, source_registers[0], source_registers[1], immediate)


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

        else:
            raise RuntimeError(f"You are not supposed to perform ALU operation on operation {opcode}")

        assert(result is not None)

        return result


class ScheduledProcessor(Processor):
    def __init__(self, program, symbols, debug=False):
        super().__init__(program, symbols, debug)

        self.RF = [0] * 33

        self.rf = RegisterFile()
        self.decoder = Decoder(symbols)
        
        self.alu = ALU()

        self.decode_queue = []
        self.issue_queue = []
        self.execute_queue = []
        self.mem_queue = []

        self.writeback_queue = []

        self.rob = ReorderBuffer()
        self.rs  = ReservationStation()
        self.lsq = LoadStoreQueue()

        self.debug=debug



    def schedule_update(update):
        self.updates.append(update)


    def tick(self, updates):
        for action, attr, val, in updates:

            # get the correct queue
            current = getattr(self, attr)

            if action == 'pop':
                # print(f'popping off {attr}')
                # print(current)
                # print(updated)
                
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

        fetch_update     = self.fetch()

        decode_update    = self.decode()

        issue_update     = self.issue()

        dispatch_update  = self.dispatch()

        execute_update   = self.execute()

        mem_update       = self.mem()

        writeback_update = self.writeback()


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

        return [('push', 'decode_queue', instruction_string), ('set', 'PC', self.PC + 1)]

    def decode(self):
        
        updates = []
        
        if (len(self.decode_queue) > 0):
           
            # parse the instruction string, compose and return an instance of the instruction class with the fields
            instruction_string = self.decode_queue[-1]
            updates += [('pop', 'decode_queue', None)]

            instruction = self.decoder.decode(instruction_string)

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
            rob_entry, rob_pointer = self.rob.add(instruction)

            # add to reservation station
            if instruction.is_mem():
                lsq_entry = self.lsq.add(instruction, rob_pointer, self.rf, self.rob)
            else:
                rs_entry = self.rs.add(instruction, rob_pointer, self.rf, self.rob)


            # rename accordingly
            if instruction.opcode != 'sw':
                self.rf.remap(instruction.target_register, rob_pointer)

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
                result = self.MEM[lsq_entry.target_address]
                updates += [('push', 'writeback_queue', (rob_tag, result))]

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

            print(f'RESULT: {result}')
            print(f'marking tag {rob_tag} as done for entry {self.rob.entries[rob_tag]}')

            # mark rob entry as done and hydrate the value
            self.rob.done(rob_tag, result)


        if self.rob.can_commit():
            rob_entry_to_commit = self.rob.lookup(self.rob.commit_pointer)

            print("COMMITTING:")
            print(rob_entry_to_commit)

            if rob_entry_to_commit.opcode in ['lw', 'sw']:
                lsq_entry_to_commit = self.lsq.lookup(self.lsq.commit_pointer)
                # assert(lsq_entry_to_commit.opcode == rob_entry_to_commit.opcode)
                print(lsq_entry_to_commit)
                
                if rob_entry_to_commit.opcode == 'sw':               
                    print(f'i am not going to write {rob_entry_to_commit.value} to address {lsq_entry_to_commit} which currently holds value { self.MEM[lsq_entry_to_commit.target_address]}')         
                    self.MEM[lsq_entry_to_commit.target_address] = rob_entry_to_commit.value

                self.lsq.free()

            self.rf.commit(rob_entry_to_commit, self.rob.commit_pointer)

            # free the rob entry and increment commit pointer
            self.rob.free()

            self.executed += 1
            

        return updates


    def broadcast(self, tag, value):
        # call the capture methods of the queues
        self.rs.capture(tag, value)
        self.lsq.capture(tag, value)
        #todo lsq capture
        


    def running(self):
        v = self.rf.ARF[31]

        return v != 1

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

        print(self.writeback_queue)
