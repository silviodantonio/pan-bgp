import logging
from threading import Lock

# This module manages all data pertaining to ASes

logger = logging.getLogger(__name__)

# Dummy RPKI prefix validator
def is_owner(as_number, prefix) -> bool:
    # TODO: implement
    return True

class ASPath():

    def __init__(self, dest_prefix: str, path: list[int], metadata: dict):
        self.dest_prefix: str = dest_prefix
        self.path: list[int] = path
        self.origin: int = path[-1]
        self.metadata: dict = metadata

class AS:

    def __init__(self, as_number: int, identity_prefix: str, attached_prefixes: list[str]):

        self.number: int = as_number
        self.identity_prefix = identity_prefix

        self.trusted = True

        self.attached_prefixes: list[str] = []
        self.add_prefixes(attached_prefixes)

        # prefix: as path
        self._rib: dict[str, ASPath] = {}
        self._rib_lock = Lock()

    def add_prefixes(self, prefixes: list[str]) -> None:
        for prefix in prefixes:
            if not is_owner(self.number, prefix):
                self.trusted = False
            else:
                self.attached_prefixes.append(prefix)

    @property
    def rib(self) -> None:
        with self._rib_lock:
            return self._rib

    @rib.setter
    def rib(self, as_paths: list[ASPath]):
        with self._rib_lock:
            for as_path in as_paths:
                self._rib[as_path.dest_prefix] = as_path

    def __str__(self):
        strings_list = []
        trusted = "trusted" if self.trusted else "untrusted"
        strings_list.append(f"AS{self.number} ({self.identity_prefix}): {trusted}")
        strings_list.append(f"Attached prefixes {len(self.attached_prefixes)}: {self.attached_prefixes}")
        strings_list.append(f"ASPaths for prefixes {len(self.rib)}: {list(self.rib.items())}")

        return "\n".join(strings_list)

    def __repr__(self):
        return self.__str__()

# functions that manage the AS "database"
ases: dict[int, AS] = {}

def add_as(as_number: int, identity_prefix: str, announced_prefixes: list):
    new_as = AS(as_number, identity_prefix, announced_prefixes)
    ases[as_number] = new_as

def add_as_paths(as_number, as_paths_list: list[dict]):

    rib = []
    for as_path in as_paths_list:
        dest_prefix = as_path["dest_prefix"]
        path = as_path["as_path"]
        metadata = as_path["metadata"]
        new_as_path = ASPath(dest_prefix, path, metadata)
        rib.append(new_as_path)

    ases[as_number].rib = rib
