from segment import Segment
import socket
import sys
import ipaddress

class Client :
    def __init__(self, port:int, path:str):
        self.ip = "127.0.0.1"
        self.port = port
        self.dest_port = 3000
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.subnet_mask = 24
        self.path = path
        self.broadcast_addr = str(ipaddress.IPv4Network(self.ip + "/" + str(self.subnet_mask), False).broadcast_address)
        self.message = bytes(f'Hello port {self.dest_port}, I am client from port {self.port}', encoding='utf8')
        self.sock.bind((self.ip, self.port))

    def send_syn_signal(self):
        syn = Segment()
        syn.set_flag(True, False, False)
        print(f'[!] Sending broadcast SYN request to port {self.dest_port}')
        self.sock.sendto(syn.pack_message(), (self.ip, self.dest_port))
    
    def recieve_syn_ack_signal(self):
        resp, addr = self.sock.recvfrom(32768)
        segment = Segment()
        segment.unpack_message(resp)
        checksum_valid = segment.is_valid_checksum
        if (not checksum_valid):
            print("[!] Error during three way handshake")
            exit(1)
        if (not (segment.flag.syn and segment.flag.ack)):
            print("[!] Error during three way handshake")
            exit(1)
        self.server_addr = addr

    def send_ack_signal(self):
        ack = Segment()
        ack.set_flag(False, True, False)
        print(f'[!] Sending unicast ACK request to port {self.dest_port}')
        self.sock.sendto(ack.pack_message(), (self.ip, self.dest_port))

    def three_way_handshake(self):
        print(f"[!] Client started at {self.ip}:{self.port}")
        print("[!] Starting three way handshake")
        self.send_syn_signal()
        print("[!] Awaiting server response")
        self.recieve_syn_ack_signal()
        self.send_ack_signal()

    def receive_file_transfer(self):
        with open(self.path, "wb") as target:
            sequence_number = 0
            eof = False
            while not eof:
                resp, addr = self.sock.recvfrom(32768)
                resp_segment = Segment()
                resp_segment.unpack_message(resp)
                checksum_valid = resp_segment.is_valid_checksum

                if (checksum_valid):
                    segment_sequence_number = resp_segment.sequence_n
                    if (segment_sequence_number == sequence_number):
                        print(f"[Segment SEQ={sequence_number}] Received, Ack sent")
                        target.write(resp_segment.data)
                        ack_segment = Segment()
                        ack_segment.sequence_n = 0
                        ack_segment.ack_n = sequence_number
                        self.sock.sendto(ack_segment.pack_message(), (self.ip, self.dest_port))
                        sequence_number += 1
                    
                    elif resp_segment.flag.fin:
                        eof = True
                        print("\n[!] FIN, stopping transfer")
                        print("[!] Sending ACK, destroying connection")
                        ack_segment = Segment()
                        ack_segment.sequence_n = 0
                        ack_segment.set_flag(False, True, False)
                        self.sock.sendto(ack_segment.pack_message(), (self.ip, self.dest_port))
                    else:
                        print("[!] Sequence number does not match, ignoring")
                        ack_segment = Segment()
                        ack_segment.sequence_n = 0
                        ack_segment.ack_n = sequence_number
                        self.sock.sendto(ack_segment.pack_message(), (self.ip, self.dest_port))
                
                elif (not checksum_valid):
                    print("Checksum failed")

    def close_socket(self):
        print(f'[!] Connection closed\n')
        self.sock.close()

if __name__ == '__main__':
    args = sys.argv
    print(args)
    main = Client(int(args[1]), args[2])
    main.three_way_handshake()
    main.receive_file_transfer()
    main.close_socket()
    
