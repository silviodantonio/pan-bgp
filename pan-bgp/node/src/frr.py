import logging
import subprocess as sp
import json
import hashlib

"""
This module contains a collections of functions that are responsible of 
interfacing with `vtysh`, the unified interface for managing frr and all its
supported daemons.
"""

logger = logging.getLogger(__name__)

_bgp_paths_hash = hashlib.sha1(b"")


def _call_vtysh(vtysh_command) -> str | None:

    # Probably the command prefix has to be more general.
    # for now it talks directly to bgpd

    logger.info(f"Invoking vtysh command: {vtysh_command}")

    command = ["vtysh", "-d", "bgpd", "-c"]
    command.extend(vtysh_command)

    command_out = None

    try:
        completed_proc = sp.run(command, check=True, capture_output=True, text=True)
        command_out = completed_proc.stdout

    except sp.CalledProcessError as proc_err:
        logging.critical(f"Couldn't interact with frr: {proc_err}")

    finally:
        return command_out


def local_asn() -> int | None:

    local_as = None

    vtysh_bgp_peer_summary = ["show ip bgp summary json"]
    vtysh_out = _call_vtysh(vtysh_bgp_peer_summary)
    vtysh_out = json.loads(vtysh_out).get("ipv4Unicast")

    local_as = int(vtysh_out.get("as"))

    return local_as


def bgp_peers_asn() -> list[int]:

    remote_ases = []

    vtysh_bgp_peer_summary = ["show ip bgp summary json"]
    vtysh_out = _call_vtysh(vtysh_bgp_peer_summary)
    vtysh_out = json.loads(vtysh_out).get("ipv4Unicast")

    bgp_peers = vtysh_out.get("peers")
    if bgp_peers is not None:
        for peer_address, peering_info in bgp_peers.items():
            remote_ases.append(int(peering_info["remoteAs"]))

    return remote_ases


def get_attached_prefixes() -> list[str]:

    attached_prefixes = []

    vtysh_bgp_self_originate = ["show ip bgp self-originate json"]
    vtysh_out = _call_vtysh(vtysh_bgp_self_originate)
    vtysh_out = json.loads(vtysh_out)

    self_orig_routes = vtysh_out.get("routes")
    if self_orig_routes is not None:
        for prefix, route_info in self_orig_routes.items():
            attached_prefixes.append(prefix)

    return attached_prefixes


class Path:

    def __init__(self, dest_prefix, dest_as, path, metadata):
        self.dest_prefix: str = dest_prefix
        self.dest_as: int = dest_as
        self.path: list[int] = path
        self.metadata: dict[str] = metadata

    def __str__(self):
        return f"{self.dest_prefix}: {self.path} ({self.metadata})"

    def __repr__(self):
        return self.__str__()


def get_as_paths() -> list[Path] :
    """
    This function extract the bestpaths from the BGP RIB.
    It returns the extracted paths as a list of Path objects.
    If the RIB didn't change since the last time this function was called,
    returns an empty list.
    """

    global _bgp_paths_hash
    paths_list = []     # init return list

    # get RIB from FRR
    get_rib_command = ["show ip bgp json"]
    full_rib = _call_vtysh(get_rib_command)
    new_bgp_paths_hash = hashlib.sha1(bytes(full_rib, "utf8"))

    logger.debug(f"""Old RIB hash: {_bgp_paths_hash.hexdigest()}
New RIB hash: {new_bgp_paths_hash.hexdigest()}""")

    # check changes in RIB
    if new_bgp_paths_hash.digest() != _bgp_paths_hash.digest() :
        logger.debug("Detected changed RIB")

        # update old hash
        _bgp_paths_hash = new_bgp_paths_hash

        # extract only data about as_paths
        bgp_paths = json.loads(full_rib).get("routes")
 
        # update path_list with new Path objects
        for prefix, paths in bgp_paths.items():
            for path in paths:
                # include only bestpaths and avoid paths for self-originated prefixes
                if path.get("bestpath") == True and path.get("path"):
                    as_path = [int(as_num) for as_num in path.get("path").split(' ')]
                    new_path_obj = Path(prefix, as_path[-1], as_path, {'bestpath': True})
                    paths_list.append(new_path_obj)

    return paths_list
