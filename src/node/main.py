import vtysh_iface

# get info about as neighbors
as_neigh = vtysh_iface.get_neighbor_as()

if __name__=='__main__':
    if as_neigh:
        print(as_neigh)
    else:
        print("No neighboring AS found")
