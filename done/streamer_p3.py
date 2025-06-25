# do not import anything else from loss_socket besides LossyUDP
import time
from concurrent.futures.thread import ThreadPoolExecutor

from lossy_socket import LossyUDP
# do not import anything else from socket except INADDR_ANY
from socket import INADDR_ANY
import struct

MAX_BYTES = 1400
HEADER_SIZE = 6
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


    def listener(self):
        while not self.closed:
            try:
                packet, addr = self.socket.recvfrom()
                if len(packet) < HEADER_SIZE:
                    continue
                header = packet[:HEADER_SIZE]
                type, flag, sqc = s.unpack(header)
                if(type ==b'D'):
                    packetdata = packet[HEADER_SIZE:]
                    self.recv_buffer[sqc] = (packetdata, flag)
                    #SENDING ACK FOR SEQUNCE_NUMBER
                    ack_header = s.pack(b'A', False, sqc)
                    self.socket.sendto(ack_header, addr)
                elif(type==b'A'):
                    self.ack_buffer[sqc] = True
                else:
                    print('Unknown packet type. Packet can either be DATA or ACK.')


            except Exception as e:
                print("listener died!")
                print(e)

    def send(self, data_bytes: bytes) -> None:
        #LOOP THROUGH PACKETS TO SEND INDIVIDUALLY
       for i in range(0, len(data_bytes)-1, MAX_BYTES):
           packet = data_bytes[i:i + MAX_BYTES]
           if i+MAX_BYTES < len(data_bytes):
               flag = False
           else:
               flag = True
           header = s.pack(b'D',flag, self.send_sqc)
           packet = header+packet
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
        self.closed = True
        self.socket.stoprecv()
        pass
