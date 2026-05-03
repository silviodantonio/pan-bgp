import logging

import as_data
import graph as g

logger = logging.getLogger(__name__)

def add_graph_nodes(graph, trusted_only=False):

    identities = []

    candidate_ases = []
    if trusted_only:
        for as_obj in as_data.ases.values():
            if as_obj.trusted:
                candidate_ases.append(as_obj)
    else:
        candidate_ases = list(as_data.ases.values())

    # known AS data
    for as_obj in candidate_ases:
        logger.debug(f"{as_obj}")

    # create node objects
    for as_obj in candidate_ases:
        as_number = as_obj.number
        logger.debug(f"Creating graph node for AS{as_number}")
        new_node = g.Node(as_number)
        logger.debug(f"Graph object: {new_node}")
        graph.nodes[as_number] = new_node
        identities.append(as_obj.identity_prefix)

    return graph

def add_trusted_edges(graph):

    ases = []
    identities = []
    for graph_node in graph.nodes.values():
        as_obj = as_data.ases[graph_node.id]
        ases.append(as_obj)
        identities.append(as_obj.identity_prefix)

    # create edges using ASpaths to identities
    for as_obj in ases:
        source_node = graph.nodes[as_obj.number]
        logger.debug(f"Adding edges to node: {source_node.id} ({id(source_node)})")
        for as_path in as_obj.rib.values():
            logger.debug(f"Evaluating path for {as_path.dest_prefix}: {as_path.path}")
            if (len(as_path.path) == 1) and (as_path.dest_prefix in identities):
                asn = as_path.path[0]
                dest_node = graph.nodes[asn]
                logger.debug(f"New edge: ({source_node.id}, {dest_node.id})")
                new_edge = g.Edge(source_node, dest_node)
                source_node.adjacency_map[dest_node] = new_edge

def add_controlled_edges(graph):

    ases = []
    identities = []
    for graph_node in graph.nodes.values():
        as_obj = as_data.ases[graph_node.id]
        ases.append(as_obj)
        identities.append(as_obj.identity_prefix)

    # create edges using ASpaths to identities
    for as_obj in ases:
        source_node = graph.nodes[as_obj.number]
        logger.debug(f"Adding edges to node: {source_node.id} ({id(source_node)})")
        for as_path in as_obj.rib.values():
            logger.debug(f"Evaluating path for {as_path.dest_prefix}: {as_path.path}")
            if as_path.dest_prefix in identities:
                logger.debug(f"{as_path.dest_prefix} is a known identity")
                # attach to first controlled ASN
                edge_cost = 0
                for asn in as_path.path:
                    if asn in graph.nodes:
                        dest_node = graph.nodes[asn]
                        logger.debug(f"New edge: ({source_node.id}, {dest_node.id})")
                        new_edge = g.Edge(source_node, dest_node, edge_cost)
                        source_node.adjacency_map[dest_node] = new_edge
                        break
                    edge_cost += 1

def compute_paths(source_as: int, dest_prefix: str, policy: str, paths_num: int):

    # A lot of duplicate code here

    if policy == "trusted_paths":

        graph = g.Graph()
        add_graph_nodes(graph, trusted_only=True)
        add_trusted_edges(graph)

        logger.info("Computed graph")
        logger.debug(graph)

        dest_as = as_data.announced_prefixes.get(dest_prefix)
        if dest_as is None:
            return [[]]
        dest_node = graph.nodes.get(dest_as.number)
        if dest_node is None:
            return [[]]

        source_as = as_data.ases[source_as]
        source_node = graph.nodes.get(source_as.number)
        if source_node is None:
            return [[]]

        paths = g.find_all_paths(graph, source_node, dest_node)

        int_paths = []
        for path in paths[:paths_num]:
            int_path = [as_obj.id for as_obj in path]
            int_paths.append(int_path)

        return int_paths

    if policy == "minimize_untrusted":

        graph = g.Graph()
        add_graph_nodes(graph)
        add_controlled_edges(graph)

        dest_as = as_data.announced_prefixes.get(dest_prefix)
        if dest_as is None:
            return [[]]
        dest_node = graph.nodes.get(dest_as.number)
        if dest_node is None:
            return [[]]

        source_as = as_data.ases[source_as]
        source_node = graph.nodes.get(source_as.number)
        if source_node is None:
            return [[]]

        paths = g.least_cost_paths(graph, source_node, dest_node, paths_num)

        int_paths = []
        for path in paths:
            int_path = [as_obj.id for as_obj in path]
            int_paths.append(int_path)

        return int_paths

    raise ValueError("Unknown policy")

