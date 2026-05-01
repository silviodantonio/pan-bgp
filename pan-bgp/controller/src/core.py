import logging

import as_data
import graph as g

logger = logging.getLogger(__name__)


def build_graph() -> g.Graph :

    graph = g.Graph()
    identities = []

    controlled_ases = as_data.ases.values()

    # known AS data
    for as_obj in controlled_ases:
        logger.debug(f"{as_obj}")

    # create node objects
    for controlled_as in controlled_ases:
        as_number = controlled_as.number
        logger.debug(f"Creating graph node for AS{as_number}")
        new_node = g.Node(as_number)
        logger.debug(f"Graph object: {new_node}")
        graph.nodes[as_number] = new_node
        identities.append(controlled_as.identity_prefix)

    # create edges using ASpaths to trusted_identities
    for controlled_as in controlled_ases:
        source_node = graph.nodes[controlled_as.number]
        logger.debug(f"Adding edges to node: {source_node.id} ({id(source_node)})")
        for as_path in controlled_as.rib.values():
            logger.debug(f"Evaluating path for {as_path.dest_prefix}: {as_path.path}")
            if as_path.dest_prefix in identities:
                logger.debug(f"{as_path.dest_prefix} is a known identity")
                # attach to first controlled ASN
                for asn in as_path.path:
                    if asn in graph.nodes:
                        dest_node = graph.nodes[asn]
                        logger.debug(f"New edge: ({source_node.id}, {dest_node.id})")
                        new_edge = g.Edge(source_node, dest_node)
                        source_node.adjacency_map[dest_node] = new_edge
                        break

    return graph


def compute_paths(source_as: int, dest_prefix: str, policy: str, paths_num: int):

    graph = build_graph()

    logger.info("Computed graph")
    logger.debug(graph)

    return [[]]
