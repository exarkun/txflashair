"""
Observe network interfaces until a particular network is joined, then sync
images from the flashair device on that network.
"""

from __future__ import unicode_literals, print_function

from sys import argv

from ipaddress import ip_address, ip_network
from netifaces import interfaces, ifaddresses

from twisted.internet.task import (
    LoopingCall,
    react,
    deferLater,
)

from .sync import Options, sync, sync_options

class Options(Options):
    optParameters = [
        ("network", None, "192.168.0.0/24", "The network on which the flashair device exists."),
    ]



def on_network(network):
    for iface in interfaces():
        for af, addrs in ifaddresses(iface):
            for addr in addrs:
                if ip_address(addr["addr"]) in network:
                    return True
    return False



def monitor(reactor, network, options):
    def check():
        if on_network(network):
            # Do it.
            d = sync(**options)
            # Then give it a rest for a while.
            d.addCallback(deferLater(reactor, 300, lambda: None))
            return d
        return None
    # Check once in a while.
    return LoopingCall(check).start(10)



def _monitor(reactor):
    o = Options()
    o.parseOptions(argv[1:])
    network = ip_network(o["network"])

    return monitor(
        reactor,
        network,
        sync_options(o),
    )


def main():
    return react(_monitor, [])
