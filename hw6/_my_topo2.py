from mininet.topo import Topo

class MyTopo(Topo):
    
    def build(self):
        h5 = self.addHost('h5', ip='10.0.0.5/24')
        h6 = self.addHost('h6', ip='10.0.0.6/24')
        h7 = self.addHost('h7', ip='10.0.0.7/24')
        h8 = self.addHost('h8', ip='10.0.0.8/24')
        
        s2 = self.addSwitch('s2')
        
        self.addLink(h5, s2)
        self.addLink(h6, s2)
        self.addLink(h7, s2)
        self.addLink(h8, s2)
        
topos = {'mytopo': (lambda: MyTopo())}