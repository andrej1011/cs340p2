# do not import anything else from loss_socket besides LossyUDP
import time
from concurrent.futures.thread import ThreadPoolExecutor
import hashlib
from lossy_socket import LossyUDP
# do not import anything else from socket except INADDR_ANY
from socket import INADDR_ANY
import struct

MAX_BYTES = 1400
HEADER_SIZE = 6
HASH_SIZE = 16
s = struct.Struct('<c?I')
ACK_TIMEOUT = 0.25

class Streamer:
    def __init__(self, dst_ip, dst_port,
                 src_ip=INADDR_ANY, src_port=0):
        """Default values listen on all network interfaces, chooses a random source port,
           and does not introduce any simulated packet loss."""
        self.socket = LossyUDP()
        self.socket.bind((src_ip, src_port))
        self.dst_ip = dst_ip
        self.dst_port = dst_port

        self.send_sqc = 0
        self.expected_sqc = 0
        self.recv_buffer = dict()
        self.ack_buffer = {}
        self.closed = False
        executor = ThreadPoolExecutor(max_workers=1)
        executor.submit(self.listener)
        self.received_fin = False


    def listener(self):
        while not self.closed:
            try:
                packet, addr = self.socket.recvfrom()
                if self.checkcorrupt(packet):
                    header = packet[:HEADER_SIZE]
                    type, flag, sqc = s.unpack(header)
                    if(type ==b'D'):
                        packetdata = packet[HEADER_SIZE+HASH_SIZE:]
                        self.recv_buffer[sqc] = (packetdata, flag)
                        #SENDING ACK FOR SEQUENCE_NUMBER
                        ack_header = s.pack(b'A', True, sqc)
                        hash = hashlib.md5(ack_header).digest()
                        ack_header = ack_header + hash
                        self.socket.sendto(ack_header, addr)
                    elif(type==b'F'):
                        self.received_fin = True
                        print("RECEIVED FIN")
                        # ACK the FIN
                        ack_header = s.pack(b'A', False, sqc)
                        hash = hashlib.md5(ack_header).digest()
                        ack_header += hash
                        self.socket.sendto(ack_header, addr)
                        print("ACKed FIN")
                    else:
                        #WE CHECKED IF PACKET IS 'A' OR 'D' IN CHECKCORRUPT
                        #THIS MEANS IF IT AIN'T 'D' THEN IT'S 'A' FOR SURE
                        self.ack_buffer[sqc] = True

            except Exception as e:
                print("listener died!")
                print(e)

    def checkcorrupt(self,packet:bytes)->bool:
        if len(packet) < HEADER_SIZE + HASH_SIZE:
            return False
        header = packet[:HEADER_SIZE]
        type, flag, sqc = s.unpack(header)
        data = b''+ packet[HEADER_SIZE+HASH_SIZE:]
        if(type != b'A' and type != b'D' and type != b'F'):
            return False
        else:
            md5check = hashlib.md5(header+data).digest()
            md5_from_header = packet[HEADER_SIZE:HEADER_SIZE+HASH_SIZE]
            if(md5check != md5_from_header):
                return False
            return True

    def send_fin(self):
        print("SENDING FIN")
        fin_seq = self.send_sqc
        header = s.pack(b'F', True, fin_seq)
        md5 = hashlib.md5(header).digest()
        packet = header + md5

        while True:
            self.socket.sendto(packet, (self.dst_ip, self.dst_port))
            send_time = time.time()
            while (time.time() - send_time) < ACK_TIMEOUT:
                if fin_seq in self.ack_buffer:
                    del self.ack_buffer[fin_seq]
                    return  # FIN ACK received
            # Timeout: resend

    def send(self, data_bytes: bytes) -> None:
        #LOOP THROUGH PACKETS TO SEND INDIVIDUALLY
       for i in range(0, len(data_bytes)-1, MAX_BYTES):
           packet = data_bytes[i:i + MAX_BYTES]
           if i+MAX_BYTES < len(data_bytes):
               flag = False
           else:
               flag = True
           header = s.pack(b'D',flag, self.send_sqc)
           hash = hashlib.md5(header+packet).digest()
           packet = header+hash+packet
           while True:
               self.socket.sendto(packet,(self.dst_ip, self.dst_port))
               send_time = time.time()
               while (time.time()-send_time) < ACK_TIMEOUT:
                   #UNTIL THE PACKET IS CONFIRMED TO BE RECEIVED, RETRANSMIT
                   if self.send_sqc in self.ack_buffer:
                       break
               if self.send_sqc in self.ack_buffer:
                   del self.ack_buffer[self.send_sqc]
                   break
           self.send_sqc += 1


    def recv(self) -> bytes:
        data = b''
        while True:
            if self.expected_sqc in self.recv_buffer:
                 packetdata,flag = self.recv_buffer.pop(self.expected_sqc)
                 data+=packetdata
                 self.expected_sqc += 1
                 if flag == True:
                    return data
            else:
                time.sleep(0.01)




    def close(self) -> None:
        """Cleans up. It should block (wait) until the Streamer is done with all
           the necessary ACKs and retransmissions"""
        # your code goes here, especially after you add ACKs and retransmissions.
        self.send_fin()
        # Wait to receive FIN from peer
        while not self.received_fin:
            time.sleep(0.05)
        time.sleep(2)
        self.closed = True
        self.socket.stoprecv()
        pass
