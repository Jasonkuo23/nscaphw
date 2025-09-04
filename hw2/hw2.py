# -*- coding: utf-8 -*-

from setting import get_hosts, get_switches, get_links, get_ip, get_mac

class host:
    def __init__(self, name, ip, mac):
        self.name = name
        self.ip = ip
        self.mac = mac 
        self.port_to = None 
        self.arp_table = dict() # maps IP addresses to MAC addresses
    def add(self, node):
        self.port_to = node
    def show_table(self):
        for i in self.arp_table:
            print(f'{i} : {self.arp_table[i]}')
    def clear(self):
        # clear ARP table entries for this host
        self.arp_table.clear()
    def update_arp(self, new):
        # update ARP table with a new entry
        self.arp_table[new[0]] = new[1]
    def handle_packet(self, node, packet):
        # handle incoming packets
        if packet[3] == 'ffff':
            if packet[2] == self.ip:
                self.update_arp([packet[0], packet[1]])
                self.send(packet[0], 2)
            else:
                return            
        elif packet[3] == self.mac:
            if packet[4] == 'ICMP_request':
                self.send(packet[0], 1)
            elif packet[4] == 'ARP_reply':
                self.update_arp([packet[0], packet[1]])
    def ping(self, dst_ip):  
        # handle a ping request
        self.send(dst_ip, 0)
        
    def send(self, dst_ip, i):
        # determine the destination MAC here
        '''
            Hint :
                if the packet is the type of arp request, destination MAC would be 'ffff'.
                else, check up the arp table.
        '''
        node = self.port_to # get node connected to this host
        packet = []
        packet.append(self.ip)
        packet.append(self.mac)
        packet.append(dst_ip)
        if dst_ip not in self.arp_table:
            dst_mac = 'ffff'
            self.update_arp([dst_ip, dst_mac])
            packet.append(dst_mac)
            node.handle_packet(self.name, packet)
            packet.pop()
            
        if i == 0:
            dst_mac = self.arp_table[dst_ip]
            packet.append(dst_mac)
            packet.append('ICMP_request')
            node.handle_packet(self.name, packet)
        elif i == 1:
            dst_mac = self.arp_table[dst_ip]
            packet.append(dst_mac)
            packet.append('ICMP_reply')
            node.handle_packet(self.name, packet)
        elif i == 2:
            dst_mac = self.arp_table[dst_ip]
            packet.append(dst_mac)
            packet.append('ARP_reply')
            node.handle_packet(self.name, packet)
        
        return

class switch:
    def __init__(self, name, port_n):
        self.name = name
        self.mac_table = dict() # maps MAC addresses to port numbers
        self.port_n = port_n # number of ports on this switch
        self.port_to = list() 
    def add(self, node): # link with other hosts or switches
        self.port_to.append(node)
    def show_table(self):
        for m in self.mac_table:
            print(f'{m} : {self.mac_table[m]}')
    def clear(self):
        # clear MAC table entries for this switch
        self.mac_table.clear()
    def update_mac(self, port, new):
        # update MAC table with a new entry
        self.mac_table[new] = port
    def send(self, idx, packet): # send to the specified port
        node = self.port_to[idx] 
        node.handle_packet(self.name, packet) 
        
    def handle_packet(self, node, packet):
        # handle incoming packets
        
        if packet[1] not in self.mac_table:
            for p in self.port_to:
                if p.name == node:
                    self.update_mac(self.port_to.index(p), packet[1])
                    break
            
        if packet[3] == 'ffff':
            for i in range(self.port_n):
                if i != self.mac_table[packet[1]]:
                    self.send(i, packet)
        else:
            if packet[3] in self.mac_table:
                self.send(self.mac_table[packet[3]], packet)
            else:
                for i in range(self.port_n):
                    if i != self.mac_table[packet[1]]:
                        self.send(i, packet)
            
def add_link(tmp1, tmp2): # create a link between two nodes
    if tmp1 in host_dict:
        node1 = host_dict[tmp1]
    else:
        node1 =  switch_dict[tmp1]
    if tmp2 in host_dict:
        node2 = host_dict[tmp2]
    else:
        node2 = switch_dict[tmp2]
    node1.add(node2)

def set_topology():
    global host_dict, switch_dict
    hostlist = get_hosts().split(' ')
    switchlist = get_switches().split(' ')
    link_command = get_links()
    ip_dic = get_ip()
    mac_dic = get_mac()
    
    host_dict = dict() # maps host names to host objects
    switch_dict = dict() # maps switch names to switch objects
    
    for h in hostlist:
        host_dict[h] = host(h, ip_dic[h], mac_dic[h])
    for s in switchlist:
        switch_dict[s] = switch(s, len(link_command.split(s))-1)
    for l in link_command.split(' '):
        [n0, n1] = l.split(',')
        add_link(n0, n1)
        add_link(n1, n0)

def ping(tmp1, tmp2): # initiate a ping between two hosts
    global host_dict, switch_dict
    if tmp1 in host_dict and tmp2 in host_dict : 
        node1 = host_dict[tmp1]
        node2 = host_dict[tmp2]
        node1.ping(node2.ip)
    else : 
        return 1 # wrong 
    return 0 # success 


def show_table(tmp): # display the ARP or MAC table of a node
    if tmp == 'all_hosts':
        print(f'ip : mac')
        for h in host_dict:
            print(f'---------------{h}:')
            host_dict[h].show_table()
        print()
    elif tmp == 'all_switches':
        print(f'mac : port')
        for s in switch_dict:
            print(f'---------------{s}:')
            switch_dict[s].show_table()
        print()
    elif tmp in host_dict:
        print(f'ip : mac\n---------------{tmp}')
        host_dict[tmp].show_table()
    elif tmp in switch_dict:
        print(f'mac : port\n---------------{tmp}')
        switch_dict[tmp].show_table()
    else:
        return 1
    return 0


def clear(tmp):
    wrong = 0
    if tmp in host_dict:
        host_dict[tmp].clear()
    elif tmp in switch_dict:
        switch_dict[tmp].clear()
    else:
        wrong = 1
    return wrong


def run_net():
    while(1):
        wrong = 0 
        command_line = input(">> ")
        command_list = command_line.strip().split(' ')
        
        if command_line.strip() =='exit':
            return 0
        if len(command_list) == 2 : 
            if command_list[0] == 'show_table':
                wrong = show_table(command_list[1])
            elif command_list[0] == 'clear' :
                wrong = clear(command_list[1])
            else :
                wrong = 1 
        elif len(command_list) == 3 and command_list[1] == 'ping' :
            wrong = ping(command_list[0], command_list[2])
        else : 
            wrong = 1
        if wrong == 1:
            print('a wrong command')

    
def main():
    set_topology()
    run_net()


if __name__ == '__main__':
    main()
