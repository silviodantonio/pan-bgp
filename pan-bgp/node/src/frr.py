import logging
import subprocess as sp
import json

"""
This module is responsible for interfacing with `vtysh`, the unified interface
for managing frr and all its supported daemons.
`vtysh` is used for getting information about bgp peers and paths
"""

logger = logging.getLogger(__name__)

def call_vtysh(vtysh_command):

        command_out = None

        try:
            completed_proc = sp.run(vtysh_command, check=True, capture_output=True, text=True)
            command_out = completed_proc.stdout

        except sp.CalledProcessError as proc_err:
            logging.critical(f"Couldn't interact with frr: {proc_err}")

        finally:
            return command_out

class BorderRouter:

    def __init__(self):
        self.local_as, self.remote_as_set = self._get_asn()
        self.attached_prefixes = self._get_attached_prefixes()

    def _get_asn(self):
        # Get both local AS number and neighbors one

        local_as = None
        remote_as_set = set()

        vtysh_bgp_peer_summary = ["vtysh", "-d", "bgpd", "-c", "show ip bgp summary json"]
        vtysh_out = call_vtysh(vtysh_bgp_peer_summary)
        vtysh_out = json.loads(vtysh_out).get("ipv4Unicast")

        local_as = vtysh_out.get("as")

        bgp_peers = vtysh_out.get("peers")
        if bgp_peers is not None:
            for peer_address, peering_info in bgp_peers.items():
                remote_as_set.add(peering_info["remoteAs"])

        return local_as, remote_as_set


    def _get_attached_prefixes(self):

        attached_prefixes = set()

        vtysh_bgp_peer_summary = ["vtysh", "-d", "bgpd", "-c", "show ip bgp self-originate json"]
        vtysh_out = call_vtysh(vtysh_bgp_peer_summary)
        vtysh_out = json.loads(vtysh_out)

        self_orig_routes = vtysh_out.get("routes")
        if self_orig_routes is not None:
            for prefix, route_info in self_orig_routes.items():
                attached_prefixes.add(prefix)

        return attached_prefixes


    def get_bgp_paths(self) -> dict:

        bgp_paths = {}

        get_rib_command = ["vtysh", "-d", "bgpd", "-c", "show ip bgp json"]
        frr_bgp_paths = json.loads(call_vtysh(get_rib_command)).get("routes")

        # prefix, paths
        for _, paths in frr_bgp_paths.items():
            for path in paths:
                # consider only bestpaths and avoid self-originated paths
                if path.get("bestpath") == True and path.get("path"):
                    as_path = [int(as_num) for as_num in path.get("path").split(' ')]
                    as_dest = int(as_path[-1])
                    bgp_paths[as_dest] = as_path

        return bgp_paths

