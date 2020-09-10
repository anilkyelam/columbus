#
# Analyze results (errors) from Lambda Neighbor Discovery run
#

import argparse
import csv
import os
from itertools import combinations 
import re


# Constants
PATTERN = r'^\s+\[Lambda-\s*([0-9]+)\]\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+).+\s+([\-0-9]+\.[0-9]+)$'
NOT_APPLICABLE = -10000
DEFAULT_PVALUE_THRESHOLD = 0.0005


class Entry:
    Id = 0
    Idread = []
    Success = False
    ClusterDist = 0.0
    RefDist = 0.0
    Pvalues = {}


# Gets hamming distance between two integers
def hamming_distance(n1, n2) : 
    x = n1 ^ n2  
    set_bits = 0
    while (x > 0) : 
        set_bits += x & 1
        x >>= 1
    return set_bits 

def avg_pairwise_distance(array, ref_pt=None):
    sum = 0
    count = 0
    for x in list(combinations(array, 2)):
        sum += hamming_distance(x[0], x[1])
        count += 1
    return sum * 1.0 / count

def avg_ref_distance(array, ref_pt):
    sum = 0
    count = 0
    for pt in array:
        sum += hamming_distance(pt, ref_pt)
        count += 1
    return sum * 1.0 / count


# Looks at how close results from the phases are (for each lambda) 
# and how close the phases are from the actual id to see correlation 
# between colocation and error rate
def error_analysis(expname, entries):
    outfile = "errorstats.csv"

    # Calculate distance metrics
    for _, e in entries.items():
        if e.Success:
            # print(e.Id, e.Success, e.Idread)
            e.ClusterDist = avg_pairwise_distance(e.Idread)
            e.RefDist = avg_ref_distance(e.Idread, e.Id)
            entries.append(e)

    # Save them for plotting
    with open(os.path.join("out", expname, outfile), 'w') as csvfile:
        first = True
        for _, e in entries.items():
            if first:
                fieldnames = ["Id", "RefDist", "ClusterDist"]
                writer = csv.writer(csvfile)
                writer.writerow(fieldnames)
                first = False
            writer.writerow([e.Id, round(e.RefDist, 2), round(e.ClusterDist, 2)])


# Pvalue threshold is an arbitrary value we picked beforehand but it does not need to be.
# We save enough data from the experiment to "repeat" it with different pvalue threshold and 
# see how the error rate is. This could let us pick the optimal pvalue threshold for minimum 
# error rate. 
def pvalue_thresh_analysis(expname, orig_entries):
    datafile = "log"
    infile = os.path.join("out", expname, datafile)
    outfile = "pvalues.csv"

    if not os.path.exists(infile):
        print("ERROR. Log file not found at {0}".format(infile))
        return

    # Read Log
    entries = {}
    with open(infile) as lines:
        for line in lines:
            matches = re.match(PATTERN, line)
            if matches:
                id = int(matches.group(1))
                phase = int(matches.group(2))
                position = int(matches.group(3))
                bit = int(matches.group(4))
                sent = int(matches.group(5))
                pvalue = float(matches.group(7))
                # print(id, phase, position, bit, sent, pvalue)

                if id not in entries:
                    entries[id] = Entry()
                    entries[id].Id = id
                    entries[id].Success = True
                    entries[id].Pvalues = {}
                if phase not in entries[id].Pvalues:    entries[id].Pvalues[phase] = {}
                entries[id].Pvalues[phase][position] = NOT_APPLICABLE if sent == 1 else pvalue

    # Sanity check: We've read everything (no holes in data from the log)
    first = None
    for _, e in entries.items():
        if not first:
            first = e
            continue
        # print(e.Id, len(e.Pvalues), len(e.Pvalues[0]))
        assert len(e.Pvalues) == len(first.Pvalues), "ERROR! Not all lambda entries from log have same number of phases."
        for p, phase in e.Pvalues.items():
            if len(phase) != len(first.Pvalues[0]):
                print(e.Id, p, len(phase), len(first.Pvalues[0]))
            assert len(phase) == len(first.Pvalues[0]), "ERROR! Not all lambda entries from log have same number of bits."

    # Sanity check: With regular pvalue threshold, we get same result as original runs
    # new_entries = apply_pvalue_threshold(entries, DEFAULT_PVALUE_THRESHOLD)
    # for e in orig_entries.values():
    #     if e.Success:
    #         assert e.Id in new_entries, "ERROR! Missing (succesful) lambda entry in the log: " + str(e.Id)
    #         # print(e.Id, e.Idread, new_entries[e.Id].Idread)
    #         assert set(e.Idread) == set(new_entries[e.Id].Idread), "ERROR! Evaluated results from log with default " + \
    #             "pvalue threshold do not match with original ones. ID: " + str(e.Id)

    # Save the p-values for plotting
    with open(os.path.join("out", expname, outfile), 'w') as csvfile:
        first = True
        for _, e in entries.items():
            for phase in e.Pvalues.values():
                for pvalue in phase.values():
                    if first:
                        fieldnames = ["Pvalues"]
                        writer = csv.writer(csvfile)
                        writer.writerow(fieldnames)
                        first = False
                    if pvalue >= 0:
                        writer.writerow([pvalue])

    # Try out different PValue Thresholds
    # Oh! This is not gonna work.. Pvaluethresh is not a free variable after all: 
    # it is used to determine next action in each Lambda. Such a waste of time... :(

    
# Applies a specified pvalue threshold on raw pvalues and evaluates final IDs read in each phase 
def apply_pvalue_threshold(entries, threshold):
    new_entries = {}
    for e in entries.values():
        ne = Entry()
        ne.Id = e.Id
        ne.Idread = []
        for pvalues in e.Pvalues.values():      # for each phase
            id_read = 0
            for bit in reversed(range(len(pvalues))):
                bit_read = 1 if (pvalues[bit] < threshold or pvalues[bit] == NOT_APPLICABLE) else 0
                id_read = 2 * id_read + bit_read
            ne.Idread.append(id_read)
        new_entries[ne.Id] = ne
    return new_entries


def main():
    # Parse and validate args
    parser = argparse.ArgumentParser("Analyze Lambda runs")
    parser.add_argument('-i', '--expname', action='store', help='Name of the experiment run, used to look for data under out/<expname>', required=True)
    parser.add_argument('-ea', '--erroraz', action='store_true', help='do error analysis on the usual results', default=False)
    parser.add_argument('-pt', '--pthreshaz', action='store_true', help='do pvalue threshold analysis from the logs to find the optimum pvalue threshold', default=True)
    args = parser.parse_args()
    
    datafile = "results.csv"
    infile = os.path.join("out", args.expname, datafile)
    if not os.path.exists(infile):
        print("ERROR. Results file not found at {0}".format(infile))
        return

    # Get original results
    orig_results = {}
    with open(infile) as csvfile:
        reader = csv.DictReader(csvfile, delimiter=',')
        for row in reader:
            e = Entry()
            e.Idread = []
            for column, value in row.items():
                if column == "Id":                  e.Id = int(value)
                if column.startswith("Phase "):     e.Idread.append(int(value))
                if column == "Success":             e.Success = bool(int(value))
            orig_results[e.Id] = e

    if args.erroraz:
        error_analysis(args.expname, orig_results)

    if args.pthreshaz:
        pvalue_thresh_analysis(args.expname, orig_results)


if __name__ == "__main__":
    main()