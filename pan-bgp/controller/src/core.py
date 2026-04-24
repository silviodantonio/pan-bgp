import logging

import graph

# singleton objects
logger = logging.getLogger(__name__)
topology_graph = graph.singleton_network_graph

def compute_paths(source_as_number: int,
                  dest_prefix: str,
                  policy: str,
                  num_paths: int) -> list[list[int]]:

    logger.debug(f"Current topology:\n{topology_graph}")

    found_paths = []

    # Check if the destination prefix is known
    dest_as = topology_graph.prefix_table.get(dest_prefix)
    if dest_as is None:
        logger.info(f'No known AS owns {dest_prefix}')
        return found_paths

    # NOTE: other two policies to add could be:
    # controlled_paths, controlled_midpoints.

    # attempt to populate the found_paths list.
    logger.info(f"Finding paths from AS{source_as_number} to AS{dest_as.number} ({dest_prefix})")
    if policy == 'trusted_paths':
        found_paths = topology_graph.trusted_paths(source_as_number, dest_as.number)
    elif policy == 'minimize_untrusted':
        # NOTE: returns only one path since dijkstra builds a minimum spanning tree.
        min_untrusted_path, cost = topology_graph.least_cost_path(source_as_number,
                                                            dest_as.number,
                                                            graph.cost_untrusted_AS, None)
        found_paths = [min_untrusted_path]

    elif policy == 'minimize_rtt':
        min_rtt_path, rtt = topology_graph.least_cost_path(source_as_number,
                                                            dest_as.number,
                                                           graph.cost_rtt, None)
        found_paths = [min_rtt_path]

    else:
        logger.info("Unknown policy")


    # Pick the number of paths requested
    found_paths = found_paths[:num_paths]

    return found_paths



def add_as(local_as_num, identity_prefix, prefix_list):
    # if not exists, build a new node
    if local_as_num not in topology_graph.ases:
        logger.info(f"Creating object for AS{local_as_num}")
        new_as = graph.AS(local_as_num, identity_prefix)

        logger.debug(f"Adding prefixes to AS{local_as_num}")
        for prefix in prefix_list:
            new_as.announces_prefix(prefix)
        topology_graph.add_as(new_as)

def add_bgp_paths(local_as_id: int, bgp_paths: list[graph.Link]):

    local_as = topology_graph.ases.get(local_as_id)
    logger.debug(f"Adding/updating paths for AS{local_as_id}")
    local_as.update_links(bgp_paths)

    logger.debug(f"Current topology:\n{topology_graph}")
