import socket
import sys
import threading
import time

class switch:
    def __init__(self, switch_id, port):
        self.switch_id = switch_id
        self.p = port
        self.neighbors = {}
        self.set = True
        self.root = switch_id
        self.ports = {}
        self.r = None
        self.last_received = None
        self.setup()
        
    def setup(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('localhost', self.p))
    
    def command(self):
        while True:
            target = input("")
            command = target.split(" ")[0]
            if command == "add":
                neighbor = int(target.split(" ")[1])
                cost = int(target.split(" ")[2])
                self.neighbors[neighbor] = cost
                if self.ports is None:
                    self.ports[0] = {"dst": neighbor, "cost": cost, "stats": 0}
                else:
                    self.ports[len(self.ports)] = {"dst": neighbor, "cost": cost,
                                                   "stats": 0, "role": ""}
                self.set = True
                for port in self.ports:
                    self.ports[port]["role"] = ""
                    self.ports[port]["stats"] = 0
            elif command == "show_root":
                print(self.root)
            elif command == "show_port":
                for port in self.ports:
                    print(f"port {port}: {self.ports[port]}")
            elif command == "send":
                dest = int(target.split(" ")[1])
                message = target.split(" ")[2]
                packet = f"p_send {self.switch_id} {dest} {message}"
                for port in self.ports:
                    if self.ports[port]["dst"] == dest:
                        if self.ports[port]["role"] == "blocked_port":
                            continue
                        self.socket.sendto(packet.encode(), ('localhost', 10000 + dest))
                    else:
                        if self.ports[port]["role"] != "blocked_port":
                            self.socket.sendto(packet.encode(), ('localhost',
                                                                 10000 + self.ports[port]["dst"]))
            elif command == "rm":
                neighbor = int(target.split(" ")[1])
                if neighbor in self.neighbors:
                    del self.neighbors[neighbor]
                    for port in self.ports:
                        if self.ports[port]["dst"] == neighbor:
                            del self.ports[port]
                            break
                

    def receive_packet(self):
        while True:
            packet = self.socket.recv(1024).decode()
            src = int(packet.split(" ")[1])
            if src not in self.neighbors:
                continue
            t = 0
            if packet.startswith("dest_port"):
                if self.root == self.switch_id:
                    continue
                n = True
                for port in self.ports:
                    if self.ports[port]["role"] == "root_port" and self.ports[port]["dst"] != src:
                        n = False
                        break
                if n:
                    self.socket.sendto(f"dest_port {self.switch_id}".encode(), ('localhost', 10000 + src))
                    continue
                for port in self.ports:
                    if self.ports[port]["dst"] == src:
                        self.ports[port]["role"] = "designated_port"
                        self.ports[port]["stats"] = 0
                        break
            for port in self.ports:
                if self.ports[port]["dst"] == src:
                    if self.ports[port]["stats"] == 1:
                        t = 1
                    break
            if t == 1:
                continue
            if packet.startswith("bpdu"):
                root = int(packet.split(" ")[2])
                if root != self.root:
                    if root < self.root:
                        self.root = root
                        print("set root to " + str(root))
                        self.set = True
                        for port in self.ports:
                            self.ports[port]["role"] = ""
                            self.ports[port]["stats"] = 0
                else:
                    self.last_received = time.time()
                
                message = "bpdu " + str(self.switch_id) + " " + str(root)
                for neighbor in self.neighbors:
                    if neighbor != root and neighbor != src:
                        self.socket.sendto(message.encode(), ('localhost', 10000 + neighbor))
                        
                    
            elif packet.startswith("root_dist"):
                for p in self.ports:
                        if self.ports[p]["role"] == "root_port":
                            self.socket.sendto(("r_root_dist" + " " + str(self.switch_id) + 
                                                " " + str(self.ports[p]["cost"])).encode(), 
                                               ('localhost', 10000 + src))
                            break
                else:
                    distance, _ = self.shortest_path_root(src)
                    self.socket.sendto(("r_root_dist " + str(self.switch_id) + " " + 
                                        str(distance)).encode(), 
                                       ('localhost', 10000 + src))

            elif packet.startswith("r_root_dist"):
                self.r = int(packet.split(" ")[2])
                
            elif packet.startswith("p_send"):
                dest = int(packet.split(" ")[2])
                message = packet.split(" ")[3]
                if dest == self.switch_id:
                    print(f"message from {src}: {message}")
                else:
                    packet = f"p_send {self.switch_id} {dest} {message}"
                    for port in self.ports:
                        if self.ports[port]["dst"] == src:
                            continue
                        if self.ports[port]["dst"] == dest:
                            if self.ports[port]["stats"] == 1:
                                continue
                            self.socket.sendto(packet.encode(), ('localhost', 10000 + dest))
                            print(f'fowarding message to {dest}')
                        else:
                            if self.ports[port]["stats"] == 0:
                                self.socket.sendto(packet.encode(), ('localhost', 10000 + self.ports[port]["dst"]))
                                print(f'fowarding message to {dest} through {self.ports[port]["dst"]}')
                            
    
    def set_port(self):
        while True:
            if self.set:
                if self.root == self.switch_id:
                    for port in self.ports:
                        self.ports[port]["role"] = "designated_port"
                    self.set = False
                    continue
                else:
                    if len(self.ports) == 1:
                        self.ports[0]["role"] = "root_port"
                        self.set = False
                        continue
                    else:
                        _, p = self.shortest_path_root(None)
                        self.ports[p]["role"] = "root_port"
                        self.socket.sendto(f"dest_port {self.switch_id}".encode(), 
                                           ('localhost', 10000 + self.ports[p]["dst"]))
                    self.set = False
                time.sleep(2)
                for p in self.ports:
                    if self.ports[p]["role"] == "":
                        self.ports[p]["role"] = "blocked_port"
                        self.ports[p]["stats"] = 1
                        self.socket.sendto(f"dest_port {self.switch_id}".encode(),
                                           ('localhost', 10000 + self.ports[p]["dst"]))
                
            
    def shortest_path_root(self, src):
        d = 999
        po = 0
        for port in self.ports:
            if self.ports[port]["dst"] == src:
                continue
            if self.ports[port]["dst"] == self.root:
                if self.ports[port]["cost"] < d:
                    d = self.ports[port]["cost"]
                    po = port
            else:
                while self.r is None:
                    self.socket.sendto((f"root_dist {self.switch_id}").encode(),
                                       ('localhost', 10000 + self.ports[port]["dst"]))
                    time.sleep(2)
                    continue
                if self.r + self.ports[port]["cost"] < d:
                    d = self.r + self.ports[port]["cost"]
                    po = port
                self.r = None
        return d, po
    
    def send_bpdu(self):
        while self.root == self.switch_id:
            bpdu = "bpdu " + str(self.switch_id) + " " + str(self.switch_id)
            for neighbor in self.neighbors:
                self.socket.sendto(bpdu.encode(), ('localhost', 10000 + neighbor))

            time.sleep(2)  
    
    def timer(self):
        while True:
            if self.last_received is None:
                continue
            if self.root != self.switch_id:
                if time.time() - self.last_received > 10:
                    print("timer expired")
                    time.sleep(1)
                    self.last_received = None
                    if(len(self.ports) == 2):
                        for port in self.ports:
                            if self.ports[port]["role"] != "root_port":
                                self.ports[port]["role"] = "root_port"
                                self.ports[port]["stats"] = 0
                                self.socket.sendto(f"dest_port {self.switch_id}".encode(),
                                                   ('localhost', 10000 + self.ports[port]["dst"]))  
                            else:
                                self.ports[port]["role"] = ""
                                self.ports[port]["stats"] = ""
            time.sleep(1)              
                
def main():
    switch_id = int(sys.argv[1])
    my_port = 10000 + switch_id
    r = switch(switch_id, my_port)
    threading.Thread(target=r.command).start()
    threading.Thread(target=r.receive_packet).start()
    threading.Thread(target=r.send_bpdu).start()
    threading.Thread(target=r.set_port).start()
    threading.Thread(target=r.timer).start()
    
if __name__ == "__main__":
    main()