import csv
from .core import decode_message, IOTAMilestoneMessage
import networkx as nx


def main():

    G = nx.DiGraph()
    with open('pyota/data/messages.csv') as csvfile:
        reader = csv.reader(csvfile)
        nlines = 0
        for row in reader:
            nlines +=1
            if nlines == 1 or nlines == 2: # skip header and a estrange row
                continue
            message = decode_message(*row)
            G.add_node(message._id)
            [G.add_edge(message._id, parent) for parent in message.parents]
            if nlines > 10_000:
                break

    nx.write_gexf(G, 'tangle.gexf')


if __name__ == "__main__":
    main()