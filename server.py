from segment import Segment
from flag import Flag
import socket
import sys
import ipaddress
import math

MAX_DATA_SIZE = 32768

class Server :
    def __init__(self, port:int, path:str):
        self.ip = '127.0.0.1'
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.subnet_mask = 24
        self.broadcast_addr = str(ipaddress.IPv4Network(self.ip + '/' + str(self.subnet_mask), False).broadcast_address)
        self.sock.bind(("", self.port))
        self.path = path
        self.message = bytes(f'Hello, I am server at port {self.port}', encoding='utf8')
        with open(self.path, 'rb') as data:
            data.seek(0,2)
            self.datasize = data.tell()
        self.nsegment = math.ceil(self.datasize / MAX_DATA_SIZE)
        self.timeout = 0.1
        self.window_size = 5
        
    def listening_clients(self):
        print(f'\nServer started at port {self.port}')
        print('Listening to broadcast address for clients.\n')

        self.client_list = []
        isWaiting = True

        while isWaiting:
            resp, addr = self.sock.recvfrom(32768)
            if(resp and addr not in self.client_list):
                self.client_list.append(addr)
                print(f'[!] Client ({addr[0]}:{addr[1]}) found')
                more = input('[?] Listen more? (y/n) ')
                if more == 'y':
                    isWaiting = True
                else:
                    isWaiting = False
            elif(resp and addr in self.client_list):
                print(f'[!] Client ({addr[0]}:{addr[1]}) already in list')
      
    def three_way_handshake(self, client:(str,int)) -> bool:
        synack = Segment()
        synack.set_flag(True, True, False)
        self.sock.sendto(synack.pack_message(), client)

        resp, addr = self.sock.recvfrom(MAX_DATA_SIZE)
        segment = Segment()
        segment.unpack_message(resp)
        checksum_valid = segment.is_valid_checksum
        if (addr == client and segment.flag.ack and checksum_valid):
            print(f"[!] Successfully conducted handshake with {client[0]}:{client[1]}")
            return True #Valid handshake
        else:
            print(f"[!] Handshake failed with {client[0]}:{client[1]}")
            return False #Invalid handshake

    
    def transfer_file(self):
        print(f'\n{len(self.client_list)} clients found:')
        if(len(self.client_list)>0):
            for i in range(len(self.client_list)):
                print(f'{i+1}. {self.client_list[i][0]}:{self.client_list[i][1]}')
            
            self.start_transfer_file()
                

    def start_transfer_file(self):
        print("\nInitiating three way handshake with clients...")
        failed_handshakes = []
        for client in self.client_list:
            print(f"[!] Sending SYN/ACK to {client[0]}:{client[1]}")
            
            # Do handshake
            success = self.three_way_handshake(client)
            if not success:
                failed_handshakes.append(client)
        
        for client in failed_handshakes:
            self.client_list.remove(client)
        
        print('\n[!] Commencing file transfer...')

        for client in self.client_list:
            print(f"[!] Sending file to [{client[0]}:{client[1]}]...")
            self.proceed_transfer_file(client)

    def proceed_transfer_file(self, client):
        self.sock.settimeout(self.timeout)
        seq_base = 0
        window_size = self.window_size
        seq_window_bound = min(seq_base+window_size, self.nsegment + 1)

        with open(self.path, "rb") as source:
            cnt = 1

            while seq_base < self.nsegment:
                print(f'\n[!] File transfer count: {cnt}')

                for i in range(seq_window_bound - seq_base):
                    data = Segment()
                    source.seek(MAX_DATA_SIZE * (seq_base + i))
                    data.data = source.read(MAX_DATA_SIZE)

                    # Set Headers
                    data.sequence_n = seq_base + i
                    data.ack_n = 0

                    # Send
                    self.sock.sendto(data.pack_message(), client)
                    print(f"[Sequence SEQ={seq_base + i}], Sent")

                for i in range(seq_window_bound - seq_base):
                    try:
                        res, addr = self.sock.recvfrom(MAX_DATA_SIZE)
                        resp = Segment()
                        resp.unpack_message(res)
                        is_checksum_success = resp.is_valid_checksum

                        str_addr = f'{addr[0]}:{addr[1]}'
                        if is_checksum_success and addr == client:
                            if resp.ack_n > seq_base and resp.ack_n < seq_window_bound:
                                seq_window_bound = min(seq_window_bound - seq_base + resp.ack_n, self.nsegment + 1)
                                seq_base = resp.ack_n
                                print(f"[Sequence SEQ={resp.ack_n}], Acked")
                             
                            else:
                                print(f'[Sequence SEQ={resp.ack_n}] NOT ACKED')
                        elif not is_checksum_success:
                            print(f'[!] Checksum failed')
                        elif addr != client:
                            print(f'[!] Source address not match')
                        else:
                            print(f'[!] Unknown error')
                    except socket.timeout:
                        print(f'[!] Response timeout')
                        break
                
                cnt += 1
            
            self.sock.settimeout(None)
            print(f'\n[!] File transfer completed, sending FIN')
            data = Segment()
            data.flag = Flag(False, False, True)
            self.sock.sendto(data.pack_message(), client)

            res, addr = self.sock.recvfrom(MAX_DATA_SIZE)
            resp = Segment()
            resp.unpack_message(res)
            while not resp.flag.ack:
                res, addr = self.sock.recvfrom(MAX_DATA_SIZE)
                resp = Segment()
                resp.unpack_message(res)
                is_checksum_success = resp.is_valid_checksum

            if resp.flag.ack:
                print(f'[!] ACK, destroying connection')
            else:
                print(f'[!] Invalid ACK segment')


    def close_socket(self):
        print(f'[!] Connection closed\n')
        self.sock.close()

if __name__ == '__main__':
    args = sys.argv
    main = Server(int(args[1]), args[2])
    main.listening_clients()
    main.transfer_file()
    main.close_socket()
    
