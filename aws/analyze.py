#
# Analyze results (errors) from Lambda Neighbor Discovery run
#

import argparse
import csv
import os
from itertools import combinations 
import re
import operator
import glob
import math 
from shutil import copyfile
import numpy as np


# Constants
BASELINE_SAMPLE_PATTERN=r'^\s+Baseline sample: Size- ([0-9]+), Mean-\s+([0-9]+)$'
BIT_STATS_PATTERN = r'^\s+\[Lambda-\s*([0-9]+)\]\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([\-0-9]+\.[0-9]+)$'
DEFAULT_PVALUE_THRESHOLD = 0.0005


# Structs
class Sample:
    def __init__(self, size, mean, std):
        self.size = size
        self.mean = mean
        self.std = std

class BitInfo:
    ksvalue = None
    sample = None

class PhaseInfo:
    base_sample = None
    bits = None

class Predecessor:
    exp_name=None
    id=None

class Entry:
    id = 0
    id_read = None          # List of ids read in phases
    maj_id = None           # Majority, if any
    success = False
    cluster_dist = 0.0
    ref_dist = 0.0
    phases = None           # Pvalue analysis
    base_samples = None     # KS-test analysis
    bit0_samples = None
    bit1_samples = None
    bit0_ks_metric = None
    bit1_ks_metric = None
    predecessors = None
    raw_data = None

class Cluster:
    id = None
    maj_id = None
    lambdas = None
    tags = None
    cpis = None


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

# Find majority elements in a list
def find_majority(arr): 
    max_count = 0
    max_val = 0
    for val in arr: 
        count = 0
        for val2 in arr: 
            if(val == val2): 
                count += 1
        if count > max_count:   
            max_val = val
            max_count = count
        
    return max_val if max_count > len(arr)/2 else None


# Looks at how close results from the phases are (for each lambda) 
# and how close the phases are from the actual id to see correlation 
# between colocation and error rate
def error_analysis(expname, entries):
    outfile = "errorstats.csv"

    # Calculate distance metrics
    for _, e in entries.items():
        if e.success:
            # print(e.id, e.success, e.id_read)
            e.cluster_dist = avg_pairwise_distance(e.id_read)
            e.ref_dist = avg_ref_distance(e.id_read, e.id)
            entries.append(e)

    # Save them for plotting
    with open(os.path.join("out", expname, outfile), 'w') as csvfile:
        first = True
        for _, e in entries.items():
            if first:
                fieldnames = ["Id", "ref_dist", "cluster_dist"]
                writer = csv.writer(csvfile)
                writer.writerow(fieldnames)
                first = False
            writer.writerow([e.id, round(e.ref_dist, 2), round(e.cluster_dist, 2)])


# Pvalue threshold is an arbitrary value we picked beforehand but it does not need to be.
# We save enough data from the experiment to "repeat" it with different ksvalue threshold and 
# see how the error rate is. This could let us pick the optimal ksvalue threshold for minimum 
# error rate. 
def ksvalue_thresh_analysis(expname, orig_entries):
    datafile = "log"
    infile = os.path.join("out", expname, datafile)
    outfile = "ksvalues.csv"

    if not os.path.exists(infile):
        print("ERROR. Log file not found at {0}".format(infile))
        return

    # Read Log
    entries = {}
    ignored_lambdas = []
    base_size = None
    with open(infile) as lines:
        for line in lines:
            # First, get baseline size (requires special handling! 0_0)
            # Don't need this anymore.
            # matches = re.match(BASELINE_SAMPLE_PATTERN, line)
            # if matches:
            #     base_size = int(matches.group(1))
            #     continue

            matches = re.match(BIT_STATS_PATTERN, line)
            if matches:
                id = int(matches.group(1))
                phase = int(matches.group(2))
                position = int(matches.group(3))
                bit = int(matches.group(4))
                sent = int(matches.group(5))
                bit_size = int(matches.group(7))
                bit_mean = int(matches.group(8))
                bit_std = int(matches.group(9))
                base_size = int(matches.group(12))
                base_mean = int(matches.group(13))
                base_std = int(matches.group(14))
                ksvalue = float(matches.group(15))
                # print(id, phase, position, bit, sent, ksvalue, base_mean, base_std, base_size, bit_mean, bit_size, bit_std)

                if id in ignored_lambdas:
                    continue

                if id not in entries:
                    entries[id] = Entry()
                    entries[id].Id = id
                    entries[id].success = True
                    entries[id].phases = {}
                if phase not in entries[id].phases:    
                    entries[id].phases[phase] = PhaseInfo()
                    entries[id].phases[phase].bits = {}
                    entries[id].phases[phase].base_sample = Sample(base_size, base_mean, base_std)
                if position not in entries[id].phases[phase].bits:
                    if sent == 0:
                        entries[id].phases[phase].bits[position] = BitInfo()
                        entries[id].phases[phase].bits[position].ksvalue = None if sent == 1 else ksvalue
                        entries[id].phases[phase].bits[position].sample = Sample(bit_size, bit_mean, bit_std)
                    else:
                        entries[id].phases[phase].bits[position] = None
                else:
                    # Duplicate logs found for a lambda, ignore this lambda altogether as a safe-side
                    print("Ignoring lambda {0}. Found duplicate log entries.".format(id))
                    ignored_lambdas.append(id)
                    del entries[id]
                
    # Sanity check: We've read everything (no holes in data from the log)
    first = None
    for _, e in entries.items():
        if not first:
            first = e
            continue
        # print(e.id, len(e.Pvalues), len(e.Pvalues[0]))
        assert len(e.phases) == len(first.phases), "ERROR! Not all lambda entries from log have same number of phases."
        for p, phase in e.phases.items():
            if len(phase.bits) != len(first.phases[0].bits):
                print(e.id, p, len(phase.bits), len(first.phases[0].bits))
            assert len(phase.bits) == len(first.phases[0].bits), "ERROR! Not all lambda entries from log have same number of bits."

    # Sanity check: With regular ksvalue threshold, we get same result as original runs
    # new_entries = apply_ksvalue_threshold(entries, DEFAULT_PVALUE_THRESHOLD)
    # for e in orig_entries.values():
    #     if e.success:
    #         assert e.id in new_entries, "ERROR! Missing (succesful) lambda entry in the log: " + str(e.id)
    #         # print(e.id, e.id_read, new_entries[e.id].id_read)
    #         assert set(e.id_read) == set(new_entries[e.id].id_read), "ERROR! Evaluated results from log with default " + \
    #             "ksvalue threshold do not match with original ones. ID: " + str(e.id)

    # Save all the stats for plotting
    with open(os.path.join("out", expname, outfile), 'w') as csvfile:
        # Write header
        fieldnames = ["Id", "Lambda", "Phase", "Bit", "Base Size", "Base Mean", "Base Std", "Size", "Mean", "Std", "KSvalue", "Mean Diff"]
        writer = csv.writer(csvfile)
        writer.writerow(fieldnames)
        
        idx = 1
        lines = []
        for _, e in entries.items():
            for pid, phase in e.phases.items():
                for bid, bit in phase.bits.items():
                    if bit is not None and -10 < bit.ksvalue < 10:
                        lines.append([idx, e.id, pid, bid, 
                            phase.base_sample.size, phase.base_sample.mean, phase.base_sample.std, 
                            bit.sample.size, bit.sample.mean, bit.sample.std, 
                            bit.ksvalue, bit.sample.mean - phase.base_sample.mean])
                        idx += 1
        
        lines = sorted(lines, key=operator.itemgetter(11))
        for line in lines:
            writer.writerow(line)

    # Try out different PValue Thresholds
    # Oh! That's not gonna work.. Pvaluethresh is not a free variable after all: 
    # it is used to determine next action in each Lambda. Such a waste of time... :(

    
# Applies a specified ksvalue threshold on raw ksvalues and evaluates final IDs read in each phase 
def apply_ksvalue_threshold(entries, threshold):
    new_entries = {}
    for e in entries.values():
        ne = Entry()
        ne.id = e.id
        ne.id_read = []
        for ksvalues in e.Pvalues.values():      # for each phase
            id_read = 0
            for bit in reversed(range(len(ksvalues))):
                bit_read = 1 if (ksvalues[bit] < threshold or ksvalues[bit] == NOT_APPLICABLE) else 0
                id_read = 2 * id_read + bit_read
            ne.id_read.append(id_read)
        new_entries[ne.id] = ne
    return new_entries


# Analyze collected latency samples and apply KS (Kolmogorov-Smirinov) and other similar 
# tests for find a threshold for classifying samples
def kstest_samples_analysis(expname, entries):
    datafile = "log"
    expdir = os.path.join("out", expname)
    outfile = "kssamples.csv"

    base_files = glob.glob("{0}/base_samples*".format(expdir))
    if len(base_files) == 0:
        print("ERROR. Cannot find samples for this experiment: {0}.".format(expname))
        return
    
    # Calculate KS-test values for all samples
    ks_values = []
    cvm_values = []
    for k in sorted(entries):
        e = entries[k]
        if e.success:
            base_path = os.path.join(expdir, "base_samples{0}".format(e.id))
            bit0_path = os.path.join(expdir, "bit0_samples{0}".format(e.id))
            bit1_path = os.path.join(expdir, "bit1_samples{0}".format(e.id))
            if os.path.exists(base_path):   e.base_samples = [int(l) for l in open(base_path).readlines()[1:]]
            if os.path.exists(bit0_path):   e.bit0_samples = [int(l) for l in open(bit0_path).readlines()[1:]]
            if os.path.exists(bit1_path):   e.bit1_samples = [int(l) for l in open(bit1_path).readlines()[1:]]
            # print(len(e.base_samples), len(e.bit0_samples), len(e.bit1_samples))

            # Perform KS-test
            if e.bit0_samples:  
                x = ks_statistic(e.base_samples, e.bit0_samples)
                ks_values.append(x)
                e.bit0_ks_metric = x[1]    # Taking Shallow mean as KS-Metric for now 
            if e.bit1_samples:  
                x = ks_statistic(e.base_samples, e.bit1_samples)
                ks_values.append(x)
                e.bit1_ks_metric = x[1]    # Taking Shallow mean as KS_Metric for now 

            # Perform CVM-test
            # CVM Test did not really show promising results
            if e.bit0_samples:  cvm_values.append(cvm_statistic(e.base_samples, e.bit0_samples))
            if e.bit1_samples:  cvm_values.append(cvm_statistic(e.base_samples, e.bit1_samples))

    # Save all the stats for plotting
    with open(os.path.join("out", expname, outfile), 'w') as csvfile:
        fieldnames = ["KS Max", "KS SMean", "KS DMean", "CVM"]
        writer = csv.writer(csvfile)
        writer.writerow(fieldnames)     # Write header
        for i, val in enumerate(ks_values):
            writer.writerow([val[0], val[1], val[2], cvm_values[i]])

    # Sort the samples based on new KS Statistic and threshold
    KS_METRIC_THRESHOLD = 3.0       # Picked for Shallow mean based on 09-10 runs
    outdir = os.path.join(expdir, "ksmetric")
    if not os.path.exists(outdir):      os.makedirs(outdir)
    for e in entries.values():
        if e.success:
            if e.bit0_samples is not None:
                outfile_name = "bit{1}_samples{0}_0".format(e.id, 0 if e.bit0_ks_metric < KS_METRIC_THRESHOLD else 1)
                copyfile(os.path.join(expdir, "bit0_samples{0}".format(e.id)), os.path.join(outdir, outfile_name))
            if e.bit1_samples is not None:
                outfile_name = "bit{1}_samples{0}_1".format(e.id, 0 if e.bit1_ks_metric < KS_METRIC_THRESHOLD else 1)
                copyfile(os.path.join(expdir, "bit1_samples{0}".format(e.id)), os.path.join(outdir, outfile_name))


# Estimates Kolmogoroc-Smirnov statistic as a measure of difference between two samples
# Assumes that number of samples ~ O(1000) and values are all between MIN_VALUE and MAX_VALUE.
# https://en.wikipedia.org/wiki/Kolmogorov%E2%80%93Smirnov_test
def ks_statistic(sample1, sample2):
    BIG_INTEGER = 1e9       # Some big number as numerator to keep computations in integer space (limits samples ~ O(1000))
    MIN_VALUE = 0
    MAX_VALUE = 100000      # Ignores values outside of this range

    sample1 = sorted([s for s in sample1 if MIN_VALUE <= s <= MAX_VALUE])
    sample2 = sorted([s for s in sample2 if MIN_VALUE <= s <= MAX_VALUE])
    m = len(sample1)
    n = len(sample2)
    s1_incr = BIG_INTEGER / m   
    s2_incr = BIG_INTEGER / n

    i = j = 0
    s1_accum = s2_accum = s1_accum_prev = s2_accum_prev = 0
    val_now = val_prev = MIN_VALUE
    max_depth = deep_sum = shallow_sum = 0 
    while i < m or j < n:
        # save previous values
        s1_accum_prev = s1_accum
        s2_accum_prev = s2_accum
        val_prev = val_now

        s1_val = sample1[i] if i < m else None
        s2_val = sample2[j] if j < n else None

        if i < m and (s2_val is None or sample1[i] <= s2_val):
            val_now = sample1[i]
            s1_accum += s1_incr
            i += 1
            # continue if there are duplicates
            while i < m and sample1[i] == sample1[i-1]:
                s1_accum += s1_incr
                i += 1

        if j < n and (s1_val is None or sample2[j] <= s1_val):
            val_now = sample2[j]
            s2_accum += s2_incr
            j += 1
            # continue if there are duplicates
            while j < n and sample2[j] == sample2[j-1]:
                s2_accum += s2_incr
                j += 1

        # print(s1_accum, s2_accum)
        depth = s1_accum - s2_accum
        deep_sum += abs(s1_accum_prev - s2_accum_prev) * (val_now - val_prev)
        shallow_sum += abs(depth) if s1_val != s2_val else abs(2 * depth)
        if abs(max_depth) < abs(depth):     max_depth = depth               # Take absolute max, but preserve the sign

    # Return max and mean KS statistics
    ks_max = max_depth * 1.0 / BIG_INTEGER
    ks_shallow_mean = shallow_sum * math.sqrt(m*n) * 1.0 / (BIG_INTEGER * (m+n) * math.sqrt(m+n))
    ks_deep_mean = deep_sum * 1.0 / (BIG_INTEGER * (MAX_VALUE - MIN_VALUE))
    return ks_max, ks_shallow_mean, ks_deep_mean


# Estimates Cramer-Von Mises statistic as a measure of difference between two samples
# https://en.wikipedia.org/wiki/Cram%C3%A9r%E2%80%93von_Mises_criterion
def cvm_statistic(sample1, sample2):
    # Get ranks of each element in the combined sample
    combined = [ (1, i, v) for i, v in enumerate(sample1) ] + [ (2, i, v) for i, v in enumerate(sample2) ]
    combined = sorted(combined, key=operator.itemgetter(2))
    
    n = len(sample1)
    m = len(sample2)
    rank1 = [None] * n
    rank2 = [None] * m
    dup_start = dup_end = 0
    for i, e in enumerate(combined):
        if i > 0 and e[2] == combined[i-1][2]:
            # A duplicate, all the work would have been done at the first occurrence
            if e[0] == 1:   rank1[e[1]] = (dup_start + dup_end) / 2
            else:           rank2[e[1]] = (dup_start + dup_end) / 2
        else:
            if (i+1) < len(combined) and e[2] == combined[i+1][2]:
                # duplicate coming up, find out how many more
                dup_start = (i+1)
                j = i
                while j+1 < len(combined) and e[2] == combined[j+1][2]:     j += 1
                dup_end = (j+1)

            if e[0] == 1:   rank1[e[1]] = (i+1)
            else:           rank2[e[1]] = (i+1)
    # print(rank1, rank2)

    sum1 = sum([ (rank - (i+1)) * (rank - (i+1)) for i, rank in enumerate(rank1) ])
    sum2 = sum([ (rank - (i+1)) * (rank - (i+1)) for i, rank in enumerate(rank2) ])
    return (n * sum1 + m * sum2) * 1.0 / (n*m*(n+m))


# Compares colocated clusters across different runs related by warm starts.
def cluster_correlation(exp_name, base_expname, entries, base_entries):
    outfile = "clusters.dat"

    # Figure out clusters
    clusters = {}
    for e in sorted(entries.values(), key=lambda x: x.id):
        if e.maj_id:
            if e.maj_id not in clusters:    clusters[e.maj_id] = []
            clusters[e.maj_id].append(e.id)

    # If base experiment run is provided, compare clusters
    if base_expname:
        total_count = 0
        found_pred_count = 0
        colocated_count = 0
        non_colocated_count = 0
        for cluster in clusters.values():
            # For every pair in the cluster, find out if thier predecessors were also a pair in base exp
            for lambda1 in cluster:
                for lambda2 in cluster:
                    if lambda1 != lambda2:
                        total_count += 1
                        lambda1_pred = next(iter([pred.id for pred in entries[lambda1].predecessors if pred.exp_name == base_expname]), None)
                        lambda2_pred = next(iter([pred.id for pred in entries[lambda2].predecessors if pred.exp_name == base_expname]), None)
                        if lambda1_pred is None or lambda2_pred is None:
                            continue
                        found_pred_count += 1

                        # check if the predecessors were co-located too
                        if lambda1_pred in base_entries and lambda2_pred in base_entries \
                                and base_entries[lambda1_pred].maj_id and base_entries[lambda2_pred].maj_id:
                            colocated_count += 1 if base_entries[lambda1_pred].maj_id == base_entries[lambda2_pred].maj_id else 0
                            non_colocated_count += 1 if base_entries[lambda1_pred].maj_id != base_entries[lambda2_pred].maj_id else 0

        print("Total number of co-located pairs: {0}".format(total_count))
        print("Total number of co-located pairs warm-started: {0} ({1}%)".format(found_pred_count, found_pred_count*100/total_count))
        print("Cases where from base run conflicts with colocation assertion of current run: {0}%".format(non_colocated_count * 100 / found_pred_count))

    # Write clusters to file
    with open(os.path.join("out", exp_name, outfile), 'w') as outfile:
        for cluster in sorted([sorted(c) for c in clusters.values()], key=operator.itemgetter(0)):
            outfile.write(" ".join([str(i) for i in sorted(cluster)]))
            outfile.write("\n")


# Analyzes metadata associated with co-located lambdas
def data_analysis(exp_name, entries):
    MAX_COLOCATED_GROUP_SIZE = 50

    # Figure out clusters and fill metadata
    idx = 1
    clusters = {}
    for e in sorted(entries.values(), key=lambda x: x.id):
        if e.maj_id:
            if e.maj_id not in clusters:
                c = Cluster()
                c.id = idx
                c.maj_id = e.maj_id
                c.lambdas = []
                c.tags = {}
                c.cpis = []
                idx += 1
                clusters[e.maj_id] = c

            clusters[e.maj_id].lambdas.append(e.id)
            if "Account" in e.raw_data or "Tag" in e.raw_data:
                tag = e.raw_data["Tag"] if "Tag" in e.raw_data else e.raw_data["Account"] 
                if tag not in clusters[e.maj_id].tags:  
                    clusters[e.maj_id].tags[tag] = 0
                clusters[e.maj_id].tags[tag] += 1
            if "CPU CPI" in e.raw_data:
                clusters[e.maj_id].cpis.append(float(e.raw_data["CPU CPI"]))

    # print([c.lambdas for c in clusters.values()])
    
    # # Print some cluster metadata
    # for cidx, cl in enumerate(clusters.keys()):
    #     for id in clusters[cl].lambdas:
    #         boot_id = entries[id].raw_data["Boot ID"]
    #         mac_addr = entries[id].raw_data["MAC Address"]
    #         ip_addr = entries[id].raw_data["IP Address"]
    #         acc_id = entries[id].raw_data["Account"]
    #         cpi = entries[id].raw_data["CPU CPI"]
    #         print(cidx, id, boot_id, mac_addr, ip_addr, acc_id, cpi)


    # Save the tag stats for plotting
    outfile = "tags.csv"
    tags = set([acc for c in clusters.values() for acc in c.tags.keys()])
    clusters_sorted = sorted(clusters.values(), key=lambda c: len(c.lambdas))
    with open(os.path.join("out", exp_name, outfile), 'w') as csvfile:
        # Write header
        fieldnames = ["Cluster"]
        for i,_ in enumerate(tags):   fieldnames.append("Tag {0}".format(i))
        for i,_ in enumerate(tags):   fieldnames.append("Tag {0} %".format(i))
        writer = csv.writer(csvfile)
        writer.writerow(fieldnames)     

        # Write values for each cluster        
        # for cidx, cluster in enumerate(clusters_sorted):
        #     values = [cidx]
        #     sum_ = 0
        #     for acc in tags:    values.append(cluster.tags.get(acc, 0))
        #     for acc in tags:    sum_ += cluster.tags.get(acc, 0)
        #     for acc in tags:    values.append(cluster.tags.get(acc, 0) * 100.0 / sum_ if sum_ > 0 else 0)
        #     writer.writerow(values)

        # Average values over each cluster size  
        cidx = 0
        size = 1
        while size <= MAX_COLOCATED_GROUP_SIZE and cidx < len(clusters_sorted):
            values = []
            cpi_values = []
            while cidx < len(clusters_sorted) and len(clusters_sorted[cidx].lambdas) == size:
                values.append([clusters_sorted[cidx].tags.get(acc, 0) for acc in tags])
                cpi_values += clusters_sorted[cidx].cpis
                cidx += 1
            values = np.mean(values, axis = 0) if values else np.empty(0)
            fractions = values * 100.0 / np.sum(values) if values.any() else np.empty(0)
            writer.writerow([size] + list(values) + list(fractions))
            # print(size, np.mean(cpi_values))
            size += 1


# Parse results.csv into Entry() objects
def parse_results_file(exp_name):
    datafile = "results.csv"
    infile = os.path.join("out", exp_name, datafile)
    if not os.path.exists(infile):
        print("ERROR. Results file not found at {0}".format(infile))
        return

    # Read each line into Entry()
    entries = {}
    with open(infile) as csvfile:
        reader = csv.DictReader(csvfile, delimiter=',')
        for row in reader:
            e = Entry()
            e.id_read = []  
            e.predecessors = []   
            for column, value in row.items():
                if column == "Id":                  e.id = int(value)
                if column.startswith("Phase "):     e.id_read.append(int(value))
                if column == "Success":             e.success = bool(int(value))
                if column == "Predecessors":   
                    for p in filter(None, value.split(",")):
                        p = p.rsplit('-', 1)
                        pred = Predecessor()
                        pred.exp_name = p[0]
                        pred.id = int(p[1])
                        e.predecessors.append(pred)
            e.maj_id = find_majority(e.id_read)
            e.raw_data = row
            entries[e.id] = e
    return entries


def main():
    # Parse and validate args
    parser = argparse.ArgumentParser("Analyze Lambda runs")
    parser.add_argument('-i', '--expname', action='store', help='Name of the experiment run, used to look for data under out/<expname>', required=True)
    parser.add_argument('-ea', '--erroraz', action='store_true', help='do error analysis on the usual results', default=False)
    parser.add_argument('-kst', '--ksthreshaz', action='store_true', help='do ksvalue threshold analysis from the logs to find the optimum ksvalue threshold', default=False)
    parser.add_argument('-ks', '--kssamplesaz', action='store_true', help='do KS test threshold analysis on the samples collected to find the optimum threshold', default=False)
    parser.add_argument('-cc', '--cluster_correlation', action='store_true', help='do cluster correlation between two different runs taking warm start into account', default=False)
    parser.add_argument('-cci', '--cc_expname', action='store', help='second run to perform cluster correlation against')
    parser.add_argument('-da', '--dataaz', action='store_true', help='do analysis on data collected about lambdas for colocated groups', default=False)
    args = parser.parse_args()
    
    entries = parse_results_file(args.expname)

    if args.erroraz:
        error_analysis(args.expname, entries)

    if args.ksthreshaz:
        ksvalue_thresh_analysis(args.expname, entries)

    if args.kssamplesaz:
        kstest_samples_analysis(args.expname, entries)

    if args.cluster_correlation:
        warm_start_count = len([e for e in entries.values() if e.success and len(e.predecessors) > 0])
        total_count = len([e for e in entries.values() if e.success])
        print("Warm start percentage for {0}: {1} %".format(args.expname, warm_start_count * 100 / total_count))

        # assert args.cc_expname, "Provide baseline experiment run for cluster corelation!"
        base_entries = parse_results_file(args.cc_expname) if args.cc_expname else None
        cluster_correlation(args.expname, args.cc_expname, entries, base_entries)

    if args.dataaz:
        data_analysis(args.expname, entries)

if __name__ == "__main__":
    main()