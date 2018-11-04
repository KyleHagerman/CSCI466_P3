'''
Created on Oct 12, 2016

@author: mwittie
'''
import queue
import threading
import time


## wrapper class for a queue of packets
class Interface:
    ## @param maxsize - the maximum size of the queue storing packets
    def __init__(self, maxsize=0):
        self.queue = queue.Queue(maxsize);
        self.mtu = None

    ##get packet from the queue interface
    def get(self):
        try:
            return self.queue.get(False)
        except queue.Empty:
            return None

    ##put the packet into the interface queue
    # @param pkt - Packet to be inserted into the queue
    # @param block - if True, block until room in queue, if False may throw queue.Full exception
    def put(self, pkt, block=False):
        self.queue.put(pkt, block)


## Implements a network layer packet (different from the RDT packet
# from programming assignment 2).
# NOTE: This class will need to be extended to for the packet to include
# the fields necessary for the completion of this assignment.
class NetworkPacket:
    ## packet encoding lengths
    id_S_length = 2
    frag_S_length = 1
    dst_addr_S_length = 5

    ##@param dst_addr: address of the destination host
    # @param data_S: packet payload
    def __init__(self, id, frag, dst_addr, data_S):
        self.dst_addr = dst_addr
        self.data_S = data_S
        self.id = id
        self.frag = frag

    ## called when printing the object
    def __str__(self):
        return self.to_byte_S()

    ## convert packet to a byte string for transmission over links
    def to_byte_S(self):
        byte_S = str(self.id).zfill(self.id_S_length)
        byte_S += str(self.frag).zfill(self.frag_S_length)
        byte_S += str(self.dst_addr).zfill(self.dst_addr_S_length)
        byte_S += self.data_S
        return byte_S

    ## extract a packet object from a byte string
    # @param byte_S: byte string representation of the packet
    @classmethod
    def from_byte_S(self, byte_S):
        #print("This is the byte_S: " + byte_S[0 : NetworkPacket.id_S_length])
        id_S = byte_S[0 : NetworkPacket.id_S_length]
        #print("This is the id_S: " + id_S)
        id = int(id_S)
        frag_S = byte_S[NetworkPacket.id_S_length : NetworkPacket.id_S_length + NetworkPacket.frag_S_length]
        frag = int(frag_S)
        dst_addr = int(byte_S[NetworkPacket.id_S_length + NetworkPacket.frag_S_length : NetworkPacket.id_S_length + NetworkPacket.frag_S_length + NetworkPacket.dst_addr_S_length])
        data_S = byte_S[NetworkPacket.id_S_length + NetworkPacket.frag_S_length + NetworkPacket.dst_addr_S_length : ]
        return self(id, frag, dst_addr, data_S)




## Implements a network host for receiving and transmitting data
class Host:

    timeout = 2

    ##@param addr: address of this node represented as an integer
    def __init__(self, addr):
        self.addr = addr
        self.in_intf_L = [Interface()]
        self.out_intf_L = [Interface()]
        self.stop = False #for thread termination

    ## called when printing the object
    def __str__(self):
        return 'Host_%s' % (self.addr)

    ## create a packet and enqueue for transmission
    # @param dst_addr: destination address for the packet
    # @param data_S: data being transmitted to the network layer
    def udt_send(self, dst_addr, data_S):
        if len(data_S) > self.out_intf_L[0].mtu:
            #print(data_S[0 : self.out_intf_L[0].mtu])
            #print(data_S[self.out_intf_L[0].mtu ::])
            p1 = NetworkPacket(1, 0, dst_addr, data_S[0:self.out_intf_L[0].mtu - 7])
            p2 = NetworkPacket(2, 0, dst_addr, data_S[self.out_intf_L[0].mtu - 7:])
            self.out_intf_L[0].put(p1.to_byte_S())
            self.out_intf_L[0].put(p2.to_byte_S())
            print('%s: sending packet "%s%s" on the out interface with mtu=%d' % (self, p1, p2, self.out_intf_L[0].mtu))
        else:
            print("Data string is less than MTU")
            p = NetworkPacket(1, 0, dst_addr, data_S)
            self.out_intf_L[0].put(p.to_byte_S()) #send packets always enqueued successfully
            print('%s: sending packet "%s" on the out interface with mtu=%d' % (self, p, self.out_intf_L[0].mtu))

    ## receive packet from the network layer
    def udt_receive(self):
        pkt_S = self.in_intf_L[0].get()
        if pkt_S is not None:
            p = NetworkPacket.from_byte_S(str(pkt_S))
            packet_id = 0
            print("Received a packet")
            if p.frag is 1:
                print("Received packet is a fragment")
                packet_id = p.id
                reconstructed_p = NetworkPacket(0,0,0,'')
                reconstructed_data_S = ''
                timeout_start = time.time()
                flag_new = 1
                while packet_id is p.id and time.time() - timeout_start < self.timeout:
                    #reconstruct the segemnted packet
                    if flag_new is 1:
                        reconstructed_data_S += p.data_S
                        print("This is the reconstructed_data_S: " + reconstructed_data_S)
                        print("This is the p.data_S: " + p.data_S)
                        flag_new = 0
                        pkt_S = None
                    reconstructed_p = NetworkPacket(packet_id, 0, p.dst_addr, reconstructed_data_S)
                    pkt_S = self.in_intf_L[0].get()
                    print("Before the second if statement pkt_S is: " + str(pkt_S))
                    print("Packet ID flag is: " + str(packet_id))
                    print("Received packet ID is: " + str(p.id))
                    if pkt_S is not None:
                        print("We received the next fragment")
                        flag_new = 1
                        p = NetworkPacket.from_byte_S(str(pkt_S))

                        print('%s: received packet "%s" on the in interface' % (self, reconstructed_p.to_byte_S()))
            else:
                print('%s: received packet "%s" on the in interface' % (self, pkt_S))

    ## thread target for the host to keep receiving data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            #receive data arriving to the in interface
            self.udt_receive()
            #terminate
            if(self.stop):
                print (threading.currentThread().getName() + ': Ending')
                return



## Implements a multi-interface router described in class
class Router:

    ##@param name: friendly router name for debugging
    # @param intf_count: the number of input and output interfaces
    # @param max_queue_size: max queue length (passed to Interface)
    def __init__(self, name, intf_count, max_queue_size):
        self.stop = False #for thread termination
        self.name = name
        #create a list of interfaces
        self.in_intf_L = [Interface(max_queue_size) for _ in range(intf_count)]
        self.out_intf_L = [Interface(max_queue_size) for _ in range(intf_count)]

    ## called when printing the object
    def __str__(self):
        return 'Router_%s' % (self.name)

    ## look through the content of incoming interfaces and forward to
    # appropriate outgoing interfaces
    def forward(self):
        for i in range(len(self.in_intf_L)):
            pkt_S = None
            try:
                #get packet from interface i
                pkt_S = self.in_intf_L[i].get()
                #if packet exists make a forwarding decision
                if pkt_S is not None:
                    p = NetworkPacket.from_byte_S(pkt_S) #parse a packet out
                    # HERE you will need to implement a lookup into the
                    # forwarding table to find the appropriate outgoing interface
                    # for now we assume the outgoing interface is also i


                    if(len(p.to_byte_S()) > self.out_intf_L[i].mtu):
                        #segement the packet
                        while(len(p.to_byte_S()) > self.out_intf_L[i].mtu):
                            #while the packet data is greater than the link MTU
                            #split the packet into pieces and save the remaining data_S to the original packet
                            print("Packet too long for MTU, segmenting...")
                            new_p = NetworkPacket(p.id, 1, p.dst_addr, p.data_S[0 : self.out_intf_L[i].mtu - 7])
                            self.out_intf_L[i].put(new_p.to_byte_S(), True)
                            print('%s: forwarding packet "%s" from interface %d to %d with mtu %d' \
                                % (self, new_p, i, i, self.out_intf_L[i].mtu))
                            p = NetworkPacket(p.id, 1, p.dst_addr, p.data_S[self.out_intf_L[i].mtu - 7 :])
                    else:
                        print("Packet forwarded from router is less than MTU")
                        self.out_intf_L[i].put(p.to_byte_S(), True)
                    print('%s: forwarding packet "%s" from interface %d to %d with mtu %d' \
                        % (self, p, i, i, self.out_intf_L[i].mtu))
            except queue.Full:
                print('%s: packet "%s" lost on interface %d' % (self, p, i))
                pass

    ## thread target for the host to keep forwarding data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            self.forward()
            if self.stop:
                print (threading.currentThread().getName() + ': Ending')
                return
