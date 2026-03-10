from collections import deque

class DirectedGraph:

    def __init__(self):
        self._adj_list = {}

    def add_node(self, node_id):
        # Do not accept nodes with duplicate id
        if node_id in self.nodes():
            raise ValueError
        else:
            self._adj_list[node_id] = []

    def nodes(self):
        return list(self._adj_list.keys())

    def del_node(self, node_id):

        # Remove node
        del self._adj_list[node_id]

        # Remove edges that were directed towards the removed node
        for adj_nodes in self._adj_list.values():
            if node_id in adj_nodes:
                adj_nodes.remove(node_id)

    def add_edge(self, start, end):
        if end not in self._adj_list[start]:
            self._adj_list[start].append(end)

    def del_edge(self, start, end):
        updated_adj_list = self._adj_list[start]
        updated_adj_list.remove(end)
        self._adj_list[start] = updated_adj_list

    def edges(self) -> list:
        edges = []
        for start, adj_nodes in self._adj_list.items():
            for adj_node in adj_nodes:
                edges.append((start, adj_node))

        return edges

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

    def __str__(self):
        return_str = ''
        for node, adj_nodes in self._adj_list.items():
            return_str += f"{node}: {adj_nodes}\n"
        return return_str
