"""
Utilities dealing with decoding IOTA messages. 

Reference specs:
https://github.com/iotaledger/protocol-rfcs/blob/master/text/0017-tangle-message/0017-tangle-message.md
https://github.com/luca-moser/protocol-rfcs/blob/signed-tx-payload/text/0000-transaction-payload/0000-transaction-payload.md
https://github.com/iotaledger/protocol-rfcs/blob/master/text/0019-milestone-payload/0019-milestone-payload.md
"""

from enum import Enum
from datetime import datetime

class PayloadType(Enum):
     TXN = 0       # Transaction
     MILESTONE = 1 # Milestone 
     IDX = 2       # Index

class IOTAMessage():
    '''In IOTA 2 the tangle contains messages, which then contain the transactions 
       or other structures that are processed by the IOTA protocol.
       Each message directly approves other messages, which are known as parents.
       NOTE: The nonce is omitted.
    '''
    def __init__(self, messageid, networkid, parents):
        # The Message ID is the BLAKE2b-256 hash of the entire serialized message.
        self._id = messageid
        self._networkid = networkid
        # Parents are other message ids. 
        self.parents = parents

    def __repr__(self):
        return f"{type(self).__name__}({self._id, self._networkid})"

class IOTAIndexMessage(IOTAMessage):
    '''
    '''
    def __init__(self, messageid, networkid, parents, index, data):
        super().__init__(messageid, networkid, parents)
        self._index = index
        self._data = data

    def looks_like_spam(self) -> bool:
        '''Guess if the index message was spam. 
        '''
        return "spam" in self._data.lower()


class IOTATxnMessage(IOTAMessage):
    '''The current IOTA protocol uses transactions (which are vertices in the Tangle), where each 
    transaction defines either an input or output. 
    A grouping of those input/output transaction vertices make up a bundle which transfers the 
    given values as an atomic unit (the entire bundle is applied or none of it). 
    The input transactions define the funds to consume and create the deposits onto the output 
    transactions target addresses. 
    '''
    def __init__(self, messageid, networkid, parents, txn_type, ninputs):
        super().__init__(messageid, networkid, parents)
        self._txn_type = txn_type
        self._inputs_count = ninputs

def get_next_uint8(data: bytes) -> int:
    return int.from_bytes(data[0:1], "little", signed=False), data[1:]

def get_next_uint16(data: bytes) -> int:
    return int.from_bytes(data[0:2], "little", signed=False), data[2:]

def get_next_uint32(data: bytes) -> int:
    return int.from_bytes(data[0:4], "little", signed=False), data[4:]

def get_next_uint16(data: bytes) -> int:
    return int.from_bytes(data[0:8], "little", signed=False), data[8:]


class IOTAMilestoneMessage(IOTAMessage):
    '''In IOTA, nodes use the milestones issued by the Coordinator to reach a consensus on which transactions are confirmed.
    '''
    def __init__(self, messageid, networkid, parents, index_number, timestamp):
        super().__init__(messageid, networkid, parents)
        self._index_number = index_number
        self._timestamp = timestamp

def decode_payload(payload: bytes):
    ''' Note that Index field must be at least 1 byte and not longer than 64 bytes for the payload to be valid.
    '''
    if payload_type(payload) == PayloadType.IDX:
        index_length = int.from_bytes(payload[4:6], "little", signed=False)
        #print(index_length)
        index = payload[6:6 + index_length]
        data =  payload[6 + index_length:]
        #print('index->' + str(index))
        #print('data->' + str(data))
        return index, data
    elif payload_type(payload) == PayloadType.MILESTONE:
        index_number = int.from_bytes(payload[4:8], "little", signed=False) 
        timestamp = payload[8:16]
        # timestamp = datetime.utcfromtimestamp(timestamp)
        return index_number, timestamp
    elif payload_type(payload) == PayloadType.TXN:
        transaction_type = int.from_bytes(payload[4:5], "little", signed=False) # Always zero?
        inputs_count =  int.from_bytes(payload[5:7], "little", signed=False)
        return transaction_type, inputs_count
    else:
        return NotImplemented
    

def payload_type(payload: bytes) -> PayloadType:
    '''Returns the payload type from the IOTA message.'''
    type_code, _ = get_next_uint32(payload)
    return PayloadType(type_code)


def decode_message(messageid : str, message : str, metadata: str) -> IOTAMessage:
    '''Decodes a IOTA message as extracted from the IOTA database.
    '''
    message = bytes.fromhex(message[2:]) # skip the 0x from the str
    networkid = message[:8]
    message = message[8:]
    parents_count, message = get_next_uint8(message)
    parents = message[:parents_count*32]
    parents = [parents[i : i+32] for i in range(0, len(parents), 32)]
    message = message[parents_count*32:]
    payload_len  =  int.from_bytes(message[:4], "little", signed=False)                      
    payload = message[4:-8] # remove the trailing nonce
    assert(len(payload) == payload_len, "Payload length incorrectly parsed.")

    if payload_type(payload) == PayloadType.IDX:
        index, data = decode_payload(payload)
        return IOTAIndexMessage(messageid, networkid, parents, index, data)
    elif payload_type(payload) == PayloadType.MILESTONE:
        index_no, ts = decode_payload(payload)
        return IOTAMilestoneMessage(messageid, networkid, parents, index_no, ts)
    elif payload_type(payload) == PayloadType.TXN:
        txn_type, input_count = decode_payload(payload)
        print(txn_type, input_count)
        return IOTATxnMessage(messageid, networkid, parents, txn_type, input_count)
    else:
        return NotImplemented



