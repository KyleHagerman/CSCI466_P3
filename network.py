'''
Created on Oct 12, 2016

@author: mwittie

CSCI 466
Nov 5, 2018
Program 3
Kyle Hagerman, Benjamin Naylor
Git: KyleHagerman, Vispanius
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

    id_S_length = 2             #the length of bytes used for the packet ID
    frag_S_length = 1           #the length of bytes used for the packet fragmentation flag
    dst_addr_S_length = 5       #the length of bytes used for the destination address

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

        byte_S = str(self.id).zfill(self.id_S_length)                   #We only have destinations 1-4 but I allowed for 2 digits to be used here
        byte_S += str(self.frag).zfill(self.frag_S_length)              #The fragmentation flag doesn't fill any zeroes because it's one byte long
        byte_S += str(self.dst_addr).zfill(self.dst_addr_S_length)
        byte_S += self.data_S
        return byte_S

    ## extract a packet object from a byte string
    # @param byte_S: byte string representation of the packet
    @classmethod
    def from_byte_S(self, byte_S):

        id_S = byte_S[0 : NetworkPacket.id_S_length]        #Pulling the ID string from the sent string of bytes
        id = int(id_S)                                      #The type cast didn't work in the above line so I just broke it into two steps
        frag_S = byte_S[NetworkPacket.id_S_length : NetworkPacket.id_S_length + NetworkPacket.frag_S_length]
        frag = int(frag_S)                                  #Same as above, two steps required to pull the integer out of the string
        dst_addr = int(byte_S[NetworkPacket.id_S_length + NetworkPacket.frag_S_length : NetworkPacket.id_S_length + NetworkPacket.frag_S_length + NetworkPacket.dst_addr_S_length])
        data_S = byte_S[NetworkPacket.id_S_length + NetworkPacket.frag_S_length + NetworkPacket.dst_addr_S_length : ]
        return self(id, frag, dst_addr, data_S)




## Implements a network host for receiving and transmitting data
class Host:

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
            #if the length of the byte string is greater than the MTU capacity, break the packet into two pieces
            #Note: this will not work for packets of byte strings larger than 2 times the first MTU

            p1 = NetworkPacket(1, 0, dst_addr, data_S[0:self.out_intf_L[0].mtu - 7])
            p2 = NetworkPacket(2, 0, dst_addr, data_S[self.out_intf_L[0].mtu - 7:])
            self.out_intf_L[0].put(p1.to_byte_S())
            self.out_intf_L[0].put(p2.to_byte_S())
            print('%s: sending two packets "%s%s" on the out interface with mtu=%d' % (self, p1, p2, self.out_intf_L[0].mtu))

        else:

            #if the byte string is less than the MTU then send normally
            p = NetworkPacket(1, 0, dst_addr, data_S)
            self.out_intf_L[0].put(p.to_byte_S()) #send packets always enqueued successfully
            print('%s: sending packet "%s" on the out interface with mtu=%d' % (self, p, self.out_intf_L[0].mtu))

    ## receive packet from the network layer
    def udt_receive(self):

        pkt_S = self.in_intf_L[0].get()             #receive packets until not None

        if pkt_S is not None:
            p = NetworkPacket.from_byte_S(str(pkt_S))
            if p.frag is 1:

                reconstructed_data_S = ''           #initialize a string to hold the reconstructed data_S
                flag_new = 1                        #flag that says we received a new packet and not None

                while p.frag is 1:
                    #reconstruct the segemnted packet
                    if flag_new is 1:

                        reconstructed_data_S += p.data_S            #append the data string to the reconstruction
                        flag_new = 0                                #reset flag
                        pkt_S = None                                #clear pkt_S to receive new packet

                    pkt_S = self.in_intf_L[0].get()                 #get a new packet
                    if pkt_S is not None:

                        flag_new = 1                                #received a new packet
                        p = NetworkPacket.from_byte_S(str(pkt_S))   #create packet object from byte string

                reconstructed_data_S += p.data_S                    #this is the last data string fragment
                if reconstructed_data_S is not '':
                    print('%s: received packet with data string: "%s" on the in interface' % (self, reconstructed_data_S))

            else:

                p = NetworkPacket.from_byte_S(str(pkt_S))           #if the packet wasn't fragmented, create packet object
                if p.data_S is not '':
                    print('%s: received packet "%s" on the in interface' % (self, p.data_S))

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
    def __init__(self, name, intf_count, max_queue_size, routing_table):
        self.stop = False #for thread termination
        self.name = name
        #create a list of interfaces
        self.in_intf_L = [Interface(max_queue_size) for _ in range(intf_count)]
        self.out_intf_L = [Interface(max_queue_size) for _ in range(intf_count)]
        #pass the hard-coded routing table to each router
        self.routing_table = routing_table

    ## called when printing the object
    def __str__(self):
        return 'Router_%s' % (self.name)

    ## look through the content of incoming interfaces and forward to
    # appropriate outgoing interfaces
    def forward(self):

        for i in range(len(self.in_intf_L)):

            pkt_S = None        #initialize the pkt_S to None

            try:
                #get packet from interface i
                pkt_S = self.in_intf_L[i].get()
                #if packet exists make a forwarding decision
                if pkt_S is not None:
                    p = NetworkPacket.from_byte_S(pkt_S) #parse a packet out
                    # HERE you will need to implement a lookup into the
                    # forwarding table to find the appropriate outgoing interface
                    # for now we assume the outgoing interface is also i

                    router_name_S = 'Router_' + self.name                           #get the name of the current router for table lookup
                    relevant_routing_table = self.routing_table[router_name_S]      #first table lookup by current router
                    lookup = relevant_routing_table[int(pkt_S[7])]                  #second table lookup by destination address

                    if(len(p.to_byte_S()) > self.out_intf_L[lookup].mtu):
                        #segement the packet

                        while(len(p.to_byte_S()) > self.out_intf_L[lookup].mtu):
                            #while the packet data is greater than the link MTU
                            #split the packet into pieces and save the remaining data_S to the original packet

                            #this new packet stores the pieces of data that can be sent at max MTU capacity
                            new_p = NetworkPacket(p.id, 1, p.dst_addr, p.data_S[0 : self.out_intf_L[lookup].mtu - 7])
                            #send the fragment
                            self.out_intf_L[lookup].put(new_p.to_byte_S(), True)
                            print('%s: forwarding packet "%s" from interface %d to %d with mtu %d' \
                                % (self, new_p, i, lookup, self.out_intf_L[lookup].mtu))
                            #reset the packet object with the remaining data string
                            p = NetworkPacket(p.id, 1, p.dst_addr, p.data_S[self.out_intf_L[lookup].mtu - 7 :])

                    #The last fragment will have a fragmentation flag of 0 to indicate it is the last fragment
                    p = NetworkPacket(p.id, 0, p.dst_addr, p.data_S)
                    #send the last fragment
                    self.out_intf_L[lookup].put(p.to_byte_S(), True)
                    print('%s: forwarding packet "%s" from interface %d to %d with mtu %d' \
                        % (self, p, i, lookup, self.out_intf_L[lookup].mtu))

            except queue.Full:
                print('%s: packet "%s" lost on interface %d' % (self, p, lookup))
                pass

    ## thread target for the host to keep forwarding data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            self.forward()
            if self.stop:
                print (threading.currentThread().getName() + ': Ending')
                return
