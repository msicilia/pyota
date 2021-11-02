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

# Some helper functions.

def get_next_uint8(data: bytes) -> int:
    return int.from_bytes(data[0:1], "little", signed=False), data[1:]

def get_next_uint16(data: bytes) -> int:
    return int.from_bytes(data[0:2], "little", signed=False), data[2:]

def get_next_uint32(data: bytes) -> int:
    return int.from_bytes(data[0:4], "little", signed=False), data[4:]

def get_next_uint64(data: bytes) -> int:
    return int.from_bytes(data[0:8], "little", signed=False), data[8:]

def get_next_bytes(data: bytes, amount: int) -> bytes:
    return data[:amount], data[amount:]

def get_parents_list(data:bytes, parents_count: int):
    parents = data[:parents_count*32]
    parents = [data[i : i+32] for i in range(0, len(parents), 32)]
    return parents, data[parents_count*32:]

def get_utxos(data:bytes, number: int):
    lst_utxos = []
    for utxo in range(number):
        input_type, data = get_next_uint8(data)
        txn_id, data = get_next_uint32(data)
        txn_index, data = get_next_uint16(data)
        lst_utxos.append(UTXO(txn_id, txn_index, input_type))
    return lst_utxos, data[7*number:]

def payload_type(payload: bytes) -> PayloadType:
    '''Returns the payload type from the IOTA message.'''
    type_code, _ = get_next_uint32(payload)
    return PayloadType(type_code)


class UTXO():
    '''
    '''
    def __init__(self, txn_id, txn_index, input_type=0):
        self.input_type = input_type
        self.txn_id = txn_id
        self.txn_idx = txn_index
    
    def __str__(self):
        return f"UTXO[{self.txn_id}:{self.txn_idx}]"
class IOTAMessage():
    '''In IOTA 2 the tangle contains messages, which then contain the transactions 
       or other structures that are processed by the IOTA protocol.
       Each message directly approves other messages, which are known as parents.
       NOTE: The nonce is omitted.
    '''
    def __init__(self, messageid: str, networkid: str, parents):
        # The Message ID is the BLAKE2b-256 hash of the entire serialized message.
        self.id = messageid
        # This field denotes whether the message was meant for mainnet, testnet, or a private net. 
        # It also marks what protocol rules apply to the message. Usually, it will be set to the 
        # first 8 bytes of the BLAKE2b-256 hash of the concatenation of the network type and the 
        # protocol version string. 
        self.networkid = networkid
        # Parents are other message ids. 
        self.parents = parents

    def __repr__(self):
        return f"{type(self).__name__}({self.id, self.networkid})"

class IOTAIndexMessage(IOTAMessage):
    '''Allows the addition of an index to the encapsulating message, as well as some arbitrary data.
    '''
    def __init__(self, messageid: str, networkid: str, parents, index: bytes, data: bytes):
        super().__init__(messageid, networkid, parents)
        self.index = index
        self.data = data

    def looks_like_spam(self) -> bool:
        '''Guess if the index message was spam. Note that it is common in IOTA that nodes send 
           spam messages to increase the security of the tangle.
        '''
        return "spam" in self._data.lower()

    def index_utf8(self) -> str:
        ''' Decode as UTF-8 replacing errors. 
        '''
        return self.index.decode("utf-8", errors="replace")

    def data_utf8(self) -> str:
        ''' Decode as UTF-8 replacing errors. 
        '''
        return self.data.decode("utf-8", errors="replace")


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
        self.txn_type = txn_type
        self.inputs_count = ninputs


class IOTAMilestoneMessage(IOTAMessage):
    '''In IOTA, nodes use the milestones issued by the Coordinator to reach a consensus on which 
       transactions are confirmed.
    '''
    def __init__(self, messageid, networkid, parents, index_number, timestamp, milestone_parents):
        super().__init__(messageid, networkid, parents)
        self.index_number = index_number
        self.timestamp = timestamp
        self.milestone_parents = parents

    def get_timestamp(self):
        return datetime.utcfromtimestamp(self.timestamp)

def decode_payload(payload: bytes):
    ''' Note that Index field must be at least 1 byte and not longer than 64 bytes for the payload to be valid.
    '''
    t = payload_type(payload)
    _, payload = get_next_uint32(payload) # remove the payload type.

    if t == PayloadType.IDX:
        index_length, payload = get_next_uint16(payload)
        index, data = get_next_bytes(payload, index_length)
        return index, data
    elif t == PayloadType.MILESTONE:
        index_number, payload = get_next_uint32(payload)
        timestamp, payload = get_next_uint64(payload)
        parents_count, payload = get_next_uint8(payload)
        mlsparents, payload = get_parents_list(payload, parents_count)
        # TODO: Decode other info
        return index_number, timestamp, mlsparents
    elif t == PayloadType.TXN:
        transaction_type, payload = get_next_uint8(payload) # Always zero?
        inputs_count, payload = get_next_uint16(payload)
        utxolst, payload = get_utxos(payload, inputs_count)
        return transaction_type, inputs_count
    else:
        return NotImplemented
    



def decode_message(messageid : str, message : str, metadata: str) -> IOTAMessage:
    '''Decodes a IOTA message as extracted from the IOTA database.
    '''
    message = bytes.fromhex(message[2:]) # skip the 0x from the str
    networkid, message = get_next_uint64(message)
    parents_count, message = get_next_uint8(message)
    parents, message = get_parents_list(message, parents_count)
    payload_len  =  int.from_bytes(message[:4], "little", signed=False)                      
    payload = message[4:-8] # remove the trailing nonce
    assert(len(payload) == payload_len, "Payload length incorrectly parsed.")

    if payload_type(payload) == PayloadType.IDX:
        index, data = decode_payload(payload)
        return IOTAIndexMessage(messageid, networkid, parents, index, data)
    elif payload_type(payload) == PayloadType.MILESTONE:
        index_no, ts, mlsparents = decode_payload(payload)
        return IOTAMilestoneMessage(messageid, networkid, parents, index_no, ts, mlsparents)
    elif payload_type(payload) == PayloadType.TXN:
        txn_type, input_count = decode_payload(payload)
        return IOTATxnMessage(messageid, networkid, parents, txn_type, input_count)
    else:
        return NotImplemented



