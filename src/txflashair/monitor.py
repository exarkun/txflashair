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
        try:
            ifaddrs = ifaddresses(iface)
        except ValueError:
            # The interface went away in the interim.
            continue

        for af, addrs in ifaddrs.items():
            for addr in addrs:
                try:
                    addr = ip_address(addr["addr"])
                except ValueError:
                    # Things like MAC addresses...
                    continue

                if addr in network:
                    return True

    return False



def _delay(ignored, reactor):
    print("Sleeping for 300 seconds.")
    return deferLater(reactor, 300, lambda: None)



def monitor(reactor, network, options):
    def check():
        print("Checking...")
        if on_network(network):
            print("On network {}: sync'ing.".format(network))
            # Do it.
            d = sync(reactor, **options)
            # Then give it a rest for a while.
            d.addCallback(_delay, reactor)
            return d

        print("Not on network {}.".format(network))
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
