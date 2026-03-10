import subprocess as sp
import json

"""
This module is responsible for interfacing with `vtysh`, the unified interface
for managing frr and all its supported daemons.
`vtysh` is used for getting information about bgp peers and paths
"""

class BorderRouter:

    def __init__(self):
        self.local_as, self.remote_as_set = self._get_as_info()

    def _get_as_info(self):
        # Returns local ASN and set of neighboring AS

        vtysh_bgp_peer_summary = ["vtysh", "-d", "bgpd", "-c", "show ip bgp summary json"]

        local_as = None
        remote_as_set = set()

        try:
            completed_proc = sp.run(vtysh_bgp_peer_summary, 
                                    check=True, capture_output=True, text=True)

            # Extract json payload from root tag
            bgp_peer_summary = json.loads(completed_proc.stdout).get('ipv4Unicast')

            # Get local ASN
            local_as = bgp_peer_summary.get("as")

            # Get neighbors ASN
            # bgp_peers contains: neighbor address, neighbor info
            bgp_peers = bgp_peer_summary.get("peers")
            if bgp_peers is not None:
                for _, peering_info in bgp_peers.items():
                    remote_as = peering_info["remoteAs"]
                    remote_as_set.add(remote_as)

        except sp.CalledProcessError as proc_err:
            # TODO: change this part into logging
            print("Couldn't invoke vtysh")
            print(proc_err)

        finally:
            return local_as, remote_as_set
