import csv
from .core import decode_message, IOTAMilestoneMessage

def main() -> None:
    """."""
    print("Hello, IOTA")
    with open('pyota/data/messages.csv') as csvfile:
        reader = csv.reader(csvfile)
        nlines = 0
        for row in reader:
            nlines +=1
            #print(row)
            if nlines == 1 or nlines == 2: # skip header and a estrange row
                continue
            message = decode_message(*row)
            if isinstance(message,  IOTAMilestoneMessage):
                print(message)
            #if nlines > 1000000:
            #    break

 


if __name__ == "__main__":
    main()