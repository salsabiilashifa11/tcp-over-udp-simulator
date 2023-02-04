import struct

class Flag:
    def __init__(self, syn, ack, fin):
        self.syn = syn
        self.ack = ack
        self.fin = fin
    
    def get_flag(self):
        flag_byte = 0b00000000
        if (self.syn):
            flag_byte |= 0b00000010
        if (self.ack):
            flag_byte |= 0b00010000
        if (self.fin):
            flag_byte |= 0b00000001
        return struct.pack("B", flag_byte)