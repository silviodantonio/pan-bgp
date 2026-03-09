import subprocess as sp
import json

"""
This module is responsible for interfacing with `vtysh`, the unified interface
for managing frr and all its supported daemons.
`vtysh` is used for getting information about bgp peers and paths
"""

VTYSH_BGP_PEER_SUMMARY = ["vtysh", "-d", "bgpd", "-c", "show ip bgp summary json"]

def get_neighbor_as():
    # Returns ASN of neighbors. If no peer is found, set is empty

    as_peers = set()

    try:
        completed_proc = sp.run(VTYSH_BGP_PEER_SUMMARY, 
                                check=True, capture_output=True, text=True)

        bgp_peer_summary = json.loads(completed_proc.stdout).get('ipv4Unicast')

        # Extract AS numbers of bgp peers
        bgp_peers = bgp_peer_summary.get("peers")
        if bgp_peers is not None:
            for _, peering_info in bgp_peers.items():
                remote_as = peering_info["remoteAs"]
                as_peers.add(remote_as)

    except sp.CalledProcessError as proc_err:
        print("Couldn't invoke vtysh")
        print(proc_err)

    finally:
        return as_peers

