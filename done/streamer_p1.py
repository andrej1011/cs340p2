# do not import anything else from loss_socket besides LossyUDP
from lossy_socket import LossyUDP
# do not import anything else from socket except INADDR_ANY
from socket import INADDR_ANY

MAX_BYTES = 1400

class Streamer:
    def __init__(self, dst_ip, dst_port,
                 src_ip=INADDR_ANY, src_port=0):
        """Default values listen on all network interfaces, chooses a random source port,
           and does not introduce any simulated packet loss."""
        self.socket = LossyUDP()
        self.socket.bind((src_ip, src_port))
        self.dst_ip = dst_ip
        self.dst_port = dst_port

    def send(self, data_bytes: bytes) -> None:
        #LOOP THROUGH PACKETS TO SEND INDIVIDUALLY
       for i in range(0, len(data_bytes)-1, MAX_BYTES):
           packet = data_bytes[i:i + MAX_BYTES]
           if i+MAX_BYTES < len(data_bytes):
               packet = b'\x00' + packet
           else:
               packet = b'\x01' + packet
           self.socket.sendto(packet,(self.dst_ip, self.dst_port))


    def recv(self) -> bytes:
        data = b''
        while True:
            packetr, addr = self.socket.recvfrom()
            flag : bytes = packetr[0]
            packetdata = packetr[1:]
            data = data + packetdata
            if flag == 1:
                return data



    def close(self) -> None:
        """Cleans up. It should block (wait) until the Streamer is done with all
           the necessary ACKs and retransmissions"""
        # your code goes here, especially after you add ACKs and retransmissions.
        pass
