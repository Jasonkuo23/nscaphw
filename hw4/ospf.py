import socket
import sys
import threading
from datetime import datetime
import time

class ospf_router:
    
    def __init__(self, router_id, host, port):
        self.id = router_id
        self.host = host
        self.port = port
        self.neighbor_table = {}
        self.routing_table = {}
        self.lsdb = {}
        self.time = datetime.now() 
        self.sock = self.create_server()
    
    def create_server(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.host, self.port))
        self.lsdb[self.id] = {"sequence": 1, "links": {}}
        self.time = datetime.now()
        return sock

    def receive_message(self):
        while True:
            data, _ = self.sock.recvfrom(1024)
            message = data.decode()
            src = int(message.split()[1])
            if message.startswith("p_SEND"):
                if int(message.split()[3][0]) != self.id:
                    destination = int(message.split()[3][0])
                    next_hop = self.routing_table[destination]["next_hop"]
                    message = " ".join(message.split()[1:])
                    print(f'Foward message from {message}')
                    self.sock.sendto(f"p_SEND {message}".encode(), (self.host, 10000 + next_hop))
                else:
                    message = " ".join(message.split()[1:])
                    src = int(message.split()[0])
                    m = " ".join(message.split()[3:])
                    print(f'Recv message from {src}: {m}')
                
            elif int(message.split()[2]) == self.id and src in self.neighbor_table:
                if message.startswith("p_HELLO"):
                    self.neighbor_table[src]["state"] = "init"
                    print(f'{datetime.now().strftime("%H:%M:%S")} - set neighbor state {src} init')
                    self.sock.sendto(f"p_HACK {self.id} {src}".encode(), (self.host, 10000 + src))

                elif message.startswith("p_HACK"):
                    self.neighbor_table[src]["state"] = "exchange"
                    print(f'{datetime.now().strftime("%H:%M:%S")} - set neighbor state {src} exchange')
                    self.sock.sendto(f"p_EXCHANGE {self.id} {src}".encode(), (self.host, 10000 + src))
                
                elif message.startswith("p_EXCHANGE"):
                    self.neighbor_table[src]["state"] = "exchange"
                    print(f'{datetime.now().strftime("%H:%M:%S")} - set neighbor state {src} exchange')
                    
                elif message.startswith("p_DBD"):
                    if self.neighbor_table[src]["state"] == "full":
                        continue    
                    send = False
                    packet = f"p_LSR {self.id} {src}"
                    for i in range(3, len(message.split()), 2):
                        lsa = int(message.split()[i])
                        sequence = int(message.split()[i + 1])
                        if lsa not in self.lsdb:
                            send = True
                            packet += f" {lsa}"
                    
                    if send:
                        self.sock.sendto(packet.encode(), (self.host, 10000 + src))
                            
                    else:
                        self.neighbor_table[src]["state"] = "full"
                        print(f'{datetime.now().strftime("%H:%M:%S")} - set neighbor state {src} full')
                        packet = f"p_DBD {self.id} {src}"
                        for lsa in self.lsdb:
                            packet += f" {lsa} {self.lsdb[lsa]['sequence']}"
                        self.sock.sendto(packet.encode(), (self.host, 10000 + src))
                    
                    self.spf()

                elif message.startswith("p_LSR"):
                    send = False
                    packet = f"p_LSU {self.id} {src}"
                    for i in range(3, len(message.split()), 1):
                        lsa = int(message.split()[i])
                        if lsa in self.lsdb:
                            packet += f" {lsa} {self.lsdb[lsa]['sequence']}"
                            for link in self.lsdb[lsa]["links"]:
                                packet += f" {link} {self.lsdb[lsa]['links'][link]}"
                            packet += " end"
                            send = True
                            
                    if send:
                        self.sock.sendto(packet.encode(), (self.host, 10000 + src))
                    
                elif message.startswith("p_LSU"):
                    update = False
                    i = 3
                    while i < len(message.split()):
                        lsa = int(message.split()[i])
                        sequence = int(message.split()[i + 1])
                        if lsa not in self.lsdb:
                            i += 2
                            self.lsdb[lsa] = {"sequence": sequence, "links": {}}
                            while message.split()[i] != "end":
                                self.update_lsa(lsa, int(message.split()[i]), int(message.split()[i + 1]), False)
                                i += 2
                            i += 1
                            update = True
                        elif sequence > self.lsdb[lsa]["sequence"]:
                            i += 2
                            self.lsdb[lsa]["sequence"] = sequence
                            u = True
                            while message.split()[i] != "end":
                                self.update_lsa(lsa, int(message.split()[i]), int(message.split()[i + 1]), u)
                                u = False
                                i += 2
                            i += 1
                            update = True
                        else:
                            i += 2
                            while message.split()[i] != "end":
                                i += 2
                            i += 1
                    self.spf()
                    if update:
                        for neighbor in self.neighbor_table:
                            if neighbor != src:
                                packet = f"p_LSU {self.id} {neighbor}"
                                for lsa in self.lsdb:
                                    packet += f" {lsa} {self.lsdb[lsa]['sequence']}"
                                    for link in self.lsdb[lsa]["links"]:
                                        packet += f" {link} {self.lsdb[lsa]['links'][link]}"
                                    packet += " end"
                                self.sock.sendto(packet.encode(), (self.host, 10000 + neighbor))
                    
                    # p_RM {self.id} {neighbor} {self.id} {self.lsdb[self.id]["sequence"]} {neighbor_id}
                elif message.startswith("p_RM"):
                    lsa = int(message.split()[3])
                    sequence = int(message.split()[4])
                    if lsa in self.lsdb and sequence > self.lsdb[lsa]["sequence"]:
                        neighbor_id = int(message.split()[5])
                        self.lsdb[lsa]["sequence"] = sequence
                        self.lsdb[lsa]["links"].pop(neighbor_id)
                        print(f'{datetime.now().strftime("%H:%M:%S")} - update LSA {lsa} {sequence}')
                        self.spf()
                        for neighbor in self.neighbor_table:
                            if neighbor != src:
                                packet = f'p_RM {self.id} {neighbor} {lsa} {sequence} {neighbor_id}'
                                self.sock.sendto(packet.encode(), (self.host, 10000 + neighbor))
                    else:
                        continue

    def enter_command(self):
        while True:
            target = input("")
            command = target.split()[0]
            if command == "addlink":
                neighbor_id = int(target.split()[1])
                cost = int(target.split()[2])
                self.add_neighbor(neighbor_id, cost)
                if self.id not in self.lsdb:
                    self.lsdb[self.id] = {"sequence": 1, "links": {}}
                else:
                    self.lsdb[self.id]["sequence"] += 1
                self.update_lsa(self.id, neighbor_id, cost, True)
                self.spf()
                for neighbor in self.neighbor_table:
                    if neighbor != neighbor_id:
                        packet = f'p_LSU {self.id} {neighbor} {self.id} {self.lsdb[self.id]["sequence"]}'
                        for link in self.lsdb[self.id]["links"]:
                            packet += f' {link} {self.lsdb[self.id]["links"][link]}'
                        packet += ' end'
                        self.sock.sendto(packet.encode(), (self.host, 10000 + neighbor))
            elif command == "setlink":
                neighbor_id = int(target.split()[1])
                cost = int(target.split()[2])
                print(f'{datetime.now().strftime("%H:%M:%S")} - update neighbor {neighbor_id} {cost}')
                self.neighbor_table[neighbor_id]["cost"] = cost
                self.update_lsa(self.id, neighbor_id, cost, True)
                self.lsdb[self.id]["sequence"] += 1
                self.spf()
                for neighbor in self.neighbor_table:
                    packet = f'p_LSU {self.id} {neighbor} {self.id} {self.lsdb[self.id]["sequence"]}'
                    for link in self.lsdb[self.id]["links"]:
                        packet += f' {link} {self.lsdb[self.id]["links"][link]}'
                    packet += ' end'
                    self.sock.sendto(packet.encode(), (self.host, 10000 + neighbor))
            elif command == "rmlink":
                neighbor_id = int(target.split()[1])
                self.neighbor_table.pop(neighbor_id)
                self.lsdb[self.id]["sequence"] += 1
                self.lsdb[self.id]["links"].pop(neighbor_id)
                print(f'{datetime.now().strftime("%H:%M:%S")} - remove neighbor {neighbor_id}')
                print(f'{datetime.now().strftime("%H:%M:%S")} - update LSA {self.id} {self.lsdb[self.id]["sequence"]}')
                self.spf()
                for neighbor in self.neighbor_table:
                    packet = f'p_RM {self.id} {neighbor} {self.id} {self.lsdb[self.id]["sequence"]} {neighbor_id}'
                    self.sock.sendto(packet.encode(), (self.host, 10000 + neighbor))
            elif command == "send":
                destination = int(target.split()[1])
                message = f'{self.id} to {destination}: {target.split()[2]}'
                next_hop = self.routing_table[destination]["next_hop"]
                while next_hop not in self.neighbor_table:
                    next_hop = self.routing_table[next_hop]["next_hop"]
                self.sock.sendto(f"p_SEND {message}".encode(), (self.host, 10000 + next_hop))
            elif command == "exit":
                sys.exit(0)
    
    def add_neighbor(self, id, cost):
        self.neighbor_table[id] = {"cost": cost, "state": "down", "dbd": []}
        print(f'{datetime.now().strftime("%H:%M:%S")} - add neighbor {id} {cost}')

    def update_lsa(self, id, neighbor_id, cost, u):
        if self.lsdb[id]["links"] == {}:
            self.lsdb[id] = {"sequence": 1, "links": {neighbor_id: cost}}
            print(f'{datetime.now().strftime("%H:%M:%S")} - add LSA {id} {self.lsdb[id]["sequence"]}')

        elif neighbor_id not in self.lsdb[id]["links"]:
            self.lsdb[id]["links"][neighbor_id] = cost
            if u:
                print(f'{datetime.now().strftime("%H:%M:%S")} - update LSA {id} {self.lsdb[id]["sequence"]}')
        elif cost != self.lsdb[id]["links"][neighbor_id]:
            self.lsdb[id]["links"][neighbor_id] = cost
            if u:
                print(f'{datetime.now().strftime("%H:%M:%S")} - update LSA {id} {self.lsdb[id]["sequence"]}')
        else:
            return

    
    # perform SPF algorithm to calculate shortest path
    def spf(self):
        old_routing_table = self.routing_table.copy()
        visited = {}
        unvisited = []
        unvisited.append(self.id)
        for router in self.lsdb:
            for r in self.lsdb[router]["links"]:
                if r not in unvisited:
                    unvisited.append(r)
        distance = {router: float('inf') for router in unvisited}
        distance[self.id] = 0
        previous = {router: None for router in unvisited}
        while unvisited:
            current = min(unvisited, key=lambda router: distance[router])
            unvisited.remove(current)
            visited[current] = distance[current]
            if current in self.lsdb:
                for neighbor in self.lsdb[current]["links"]:
                    if neighbor in unvisited:
                        new_distance = visited[current] + self.lsdb[current]["links"][neighbor]
                        if new_distance < distance[neighbor]:
                            distance[neighbor] = new_distance
                            previous[neighbor] = current
                                
        # update routing table
        for router in visited:
            if router != self.id:
                if previous[router] == self.id:
                    self.routing_table[router] = {"next_hop": router, "cost": visited[router]}
                else:
                    if previous[router] not in self.neighbor_table:
                        next_hop = previous[router]
                        while next_hop not in self.neighbor_table:
                            next_hop = previous[next_hop]
                        if next_hop != self.routing_table[next_hop]["next_hop"]:
                            next_hop = self.routing_table[next_hop]["next_hop"]
                        self.routing_table[router] = {"next_hop": next_hop, "cost": visited[router]}
                    else:
                        self.routing_table[router] = {"next_hop": previous[router], "cost": visited[router]}

        for router in self.routing_table:
            if router not in old_routing_table:
                print(f'{datetime.now().strftime("%H:%M:%S")} - add route {router} {self.routing_table[router]["next_hop"]} {self.routing_table[router]["cost"]}')
            elif self.routing_table[router] != old_routing_table[router]:
                print(f'{datetime.now().strftime("%H:%M:%S")} - update route {router} {self.routing_table[router]["next_hop"]} {self.routing_table[router]["cost"]}')
        
    def handle_neighbor(self):
        while True:
            for neighbor in self.neighbor_table:
                if self.neighbor_table[neighbor]["state"] == "down":
                    self.sock.sendto(f"p_HELLO {self.id} {neighbor}".encode(), (self.host, 10000 + neighbor))
                
                
                elif self.neighbor_table[neighbor]["state"] == "exchange":
                    packet = f"p_DBD {self.id} {neighbor}"
                    for lsa in self.lsdb:
                        packet += f" {lsa} {self.lsdb[lsa]['sequence']}"
                    self.sock.sendto(packet.encode(), (self.host, 10000 + neighbor))
            
            # update LSA every 15 seconds
            if (datetime.now() - self.time).seconds > 15:
                self.time = datetime.now()
                self.lsdb[self.id]["sequence"] += 1
                 
            time.sleep(1)

def main():
    router_id = int(sys.argv[1])
    my_port = 10000 + router_id
    host = 'localhost'

    router = ospf_router(router_id, host, my_port)

    # Start thread to listen for incoming connections
    threading.Thread(target=router.receive_message).start()
    threading.Thread(target=router.handle_neighbor).start()
    
    # Allow user to send messages to other routers
    router.enter_command()

if __name__ == '__main__':
    main()