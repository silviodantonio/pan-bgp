from collections import deque

class DirectedGraph:

    def __init__(self):
        self._adj_list = {}
        self._in_degree = {}
    
    def in_degree(self, node_id):
        if node_id in self._in_degree:
            return self._in_degree[node_id]
        else:
            return None

    def add_node(self, node_id):
        # Do not accept nodes with duplicate id
        if node_id in self.nodes():
            raise ValueError
        else:
            self._adj_list[node_id] = []
            self._in_degree[node_id] = 0

    def nodes(self):
        return list(self._adj_list.keys())

    def del_node(self, node_id):
        # Reduce degree of adjacent nodes
        for adj_node in self._adj_list[node_id]:
            self._in_degree[adj_node] -= 1
        
        # Remove node
        del self._adj_list[node_id]
        del self._in_degree[node_id]

        # Remove edges that were directed towards the removed node
        for adj_nodes in self._adj_list.values():
            if node_id in adj_nodes:
                adj_nodes.remove(node_id)

    def add_edge(self, start, end):
        if end not in self._adj_list[start]:
            self._adj_list[start].append(end)
            self._in_degree[end] += 1

    def del_edge(self, start, end):
        updated_adj_list = self._adj_list[start]
        updated_adj_list.remove(end)
        self._adj_list[start] = updated_adj_list
        self._in_degree[end] -= 1

    def edges(self) -> list:
        edges = []
        for start, adj_nodes in self._adj_list.items():
            for adj_node in adj_nodes:
                edges.append((start, adj_node))
            
        return edges

    def exists_cycle(self) -> bool:
        ordering = self._topological_ordering()
        if len(ordering) == len(self._adj_list):
            return False
        return True
    
    def bfs(self, root) -> list:

        q = deque()
        visited = []

        q.append(root)

        while len(q) != 0:

            node = q.popleft()

            if node not in visited:
                visited.append(node)

                for adj_node in self._adj_list[node]:
                    if adj_node not in visited:
                        q.append(adj_node)

        return visited



    def _topological_ordering(self):
        # Attempt to build a topological order using Kahn's algo.

        ordering = []
        partial_ordering = []

        degrees = {}
        
        for node in self._adj_list.keys():
            degrees[node] = 0
    
        for adj_nodes in self._adj_list.values():
            for tail_node in adj_nodes:
                degrees[tail_node] += 1

        while True:
            for node, degree in degrees.items():
                if degree == 0:
                    partial_ordering.append(node)
            
            if len(partial_ordering) == 0:
                break

            for node in partial_ordering:
                del degrees[node]
                for adj_node in self._adj_list[node]:
                    degrees[adj_node] -= 1

            ordering += partial_ordering
            partial_ordering = []

        return ordering
    
    def _all_topological_ordering(self):

        in_degree = {node: 0 for node in list(self._adj_list.keys())}
        for adj_list in self._adj_list.values():
            for adj_node in adj_list:
                in_degree[adj_node] += 1

        orderings = []
        self._topological_rec(orderings, [], in_degree)
        
        filtered_orderings = [ordering for ordering in orderings if len(ordering) == len(self._adj_list)]
        return filtered_orderings

    def _topological_rec(self, orderings, order, in_degrees):
        # Non-selected nodes with 0 in_degree
        graph_nodes = list(self._adj_list.keys())
        available = [node for node in graph_nodes if node not in order and in_degrees[node] == 0]

        if len(available) == 0:
            return orderings.append(order)
        else:
            # Compute the other orderings (i.e.: a list with the other orderings)
            for avail_node in available:
                
                # Add avail_node to ordering
                order_copy = order.copy()
                order_copy.append(avail_node)

                # Update in_degrees
                in_degrees_copy = in_degrees.copy()
                for adj_node in self._adj_list[avail_node]:
                    in_degrees_copy[adj_node] -= 1

                self._topological_rec(orderings, order_copy, in_degrees_copy)

    
    def __str__(self):
        return_str = ''
        for node, adj_nodes in self._adj_list.items():
            return_str += f"{node}: {adj_nodes}\n"
        return return_str
