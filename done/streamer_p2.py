# do not import anything else from loss_socket besides LossyUDP
from lossy_socket import LossyUDP
# do not import anything else from socket except INADDR_ANY
from socket import INADDR_ANY
import struct

MAX_BYTES = 1400
HEADER_SIZE = 5

s = struct.Struct('<?I')

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

    def send(self, data_bytes: bytes) -> None:
        #LOOP THROUGH PACKETS TO SEND INDIVIDUALLY
       for i in range(0, len(data_bytes)-1, MAX_BYTES):
           packet = data_bytes[i:i + MAX_BYTES]
           if i+MAX_BYTES < len(data_bytes):
               flag = False
           else:
               flag = True
           header = s.pack(flag, self.send_sqc)
           packet = header+packet
           self.socket.sendto(packet,(self.dst_ip, self.dst_port))
           self.send_sqc += 1

    def recv(self) -> bytes:
        data = b''
        while True:
            packet, addr = self.socket.recvfrom()
            header = packet[:HEADER_SIZE]
            packetdata = packet[HEADER_SIZE:]
            flag, sqc = s.unpack(header)

            print(f"RECEIVED PACKET{sqc}")
            print(f"EXPECTED PACKET{self.expected_sqc}")
            print(packetdata)
            if sqc > self.expected_sqc:
                self.recv_buffer[sqc] = (packetdata,flag)
            elif sqc == self.expected_sqc:
                data += packetdata
                self.expected_sqc += 1
                while (self.expected_sqc) in self.recv_buffer:
                    buffer,bflag = self.recv_buffer.pop(self.expected_sqc)
                    data+=buffer
                    self.expected_sqc += 1
                    if bflag:
                        flag = True

                if flag == True:
                    return data



    def close(self) -> None:
        """Cleans up. It should block (wait) until the Streamer is done with all
           the necessary ACKs and retransmissions"""
        # your code goes here, especially after you add ACKs and retransmissions.
        pass
