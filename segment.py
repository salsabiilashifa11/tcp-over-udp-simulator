from flag import Flag
import struct

class Segment:
    def __init__(self):
        self.sequence_n = 0
        self.ack_n = 0
        self.flag = Flag(False, False, False)
        self.checksum = 0
        self.data = b''

    def unpack_message(self, message):
        header = struct.unpack('IIBxH', message[0:12])
        self.sequence_n = header[0]
        self.ack_n = header[1]
        self.flag = Flag(bool(header[2] & 0b00000010), bool(header[2] & 0b00010000), bool(header[2] & 0b00000001))
        self.checksum = header[3]
        self.data = message[12:]

    def pack_message(self):
        self.checksum = self.get_checksum()
        message = b''
        message += struct.pack('I', self.sequence_n)
        message += struct.pack('I', self.ack_n)
        message += self.flag.get_flag()
        message += struct.pack('x')
        message += struct.pack('H', self.checksum)
        message += self.data
        return message

    def set_flag(self, syn, ack, fin):
        self.flag = Flag(syn, ack, fin)

    def get_checksum(self):
        flag_unpacked = struct.unpack('B', self.flag.get_flag())[0]
        checksum = 0
        checksum = (checksum + self.sequence_n) & 0xFFFF
        checksum = (checksum + self.ack_n) & 0xFFFF
        checksum = (checksum + flag_unpacked) & 0xFFFF
        checksum = (checksum + self.checksum) & 0xFFFF
        for i in range(0, len(self.data), 2):
            buffer = self.data[i:i+2]
            if len(buffer) == 1:
                buffer += struct.pack("x")
            chunk = struct.unpack("H", buffer)[0]
            checksum = (checksum + chunk) & 0xFFFF
        checksum = 0xFFFF - checksum
        return checksum

    def is_valid_checksum(self):
        return self.get_checksum() == 0
