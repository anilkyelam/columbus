import sys
import os
import re
import math
from datetime import datetime
from datetime import timedelta
import time
import random
import matplotlib
import matplotlib.pyplot as plt
from collections import Counter, defaultdict
import argparse
import pandas as pd
from enum import Enum
import scipy.stats as scstats


colors = ['orange','orangered','brown','r','c','k', 'm', 'g']
linetypes = ['g-','g--','g-+']
markers = ['x','+','o','s','+', '|', '^']

class PlotType(Enum):
    line = 'line'
    scatter = 'scatter'
    bar = 'bar'

    def __str__(self):
        return self.value


# Argument Parser
def parse_args():
    parser = argparse.ArgumentParser("Python Generic Plotter")

    parser.add_argument('-d', '--datafile', 
        action='append', 
        help='path to the data file, multiple values are allowed', 
        required=True)

    parser.add_argument('-o', '--output', 
        action='store', 
        help='path to the output plot png', 
        default="result.png")

    parser.add_argument('-p', '--print_', 
        action='store_true', 
        help='print data (with nicer format) instead of plot', 
        default=False)
    
    # plot options
    parser.add_argument('-z', '--ptype', 
        action='store', 
        help='type of the plot. Defaults to line',
        type=PlotType, 
        choices=list(PlotType), 
        default=PlotType.line)

    parser.add_argument('-t', '--ptitle', 
        action='store', 
        help='title of the plot')

    parser.add_argument('-xc', '--xcol', 
        action='store', 
        help='X column  from csv file. Defaults to row index if not provided.', 
        required=False)

    parser.add_argument('-yc', '--ycol', 
        action='append', 
        help='Y column from csv file, multiple values are allowed', 
        required=True)

    parser.add_argument('-xl', '--xlabel', 
        action='store', 
        help='Custom x-axis label')

    parser.add_argument('-yl', '--ylabel', 
        action='store', 
        help='Custom y-axis label')

    parser.add_argument('-l', '--plabel', 
        action='append', 
        help='plot label, can provide one label per ycol or datafile')

    args = parser.parse_args()
    return args


def main():
    args = parse_args()

    # Plot can be: 
    # 1. One datafile with multiple ycolumns plotted against single xcolumn
    # 2. Single ycolumn from multiple datafiles plotted against an xcolumn
    if len(args.datafile) > 1 and len(args.ycol) > 1:
        print("Only one of datafile or ycolumn arguments can provide multiple values")
        return -1

    num_plots = len(args.datafile) if len(args.datafile) > 1 else len(args.ycol)
    if args.plabel and len(args.plabel) != num_plots:
        print("If plot labels are provided, they must be provided for all the plots and are mapped one-to-one in input order")
        return -1


    xcol = args.xcol 
    xlabel = args.xlabel if args.xlabel else args.xcol
    ylabel = args.ylabel if args.ylabel else args.ycol

    cidx = 0
    midx = 0
    lidx = 0
    aidx = 0

    font = {'family' : 'normal',
            'weight' : 'normal',
            'size'   : 12}
    matplotlib.rc('font', **font)

    if args.print_:   
        samples = []
        for idx, datafile in enumerate(args.datafile):
            if not os.path.exists(datafile):
                print("Datafile '{0}' does not exist" % datafile)
                return -1

            df = pd.read_csv(datafile)
            for ycol in args.ycol:
                label = "{0}:{1}".format(datafile, ycol)
                samples.append(df[ycol])
                print("{0} {1} {2}".format(label, df[ycol].mean(), df[ycol].std()))
            continue

        # Also print p and t values if there are two samples.
        if (len(samples) == 2):
            (tval, pval) = scstats.ttest_rel(samples[0], samples[1])
            print("T-Value: {0}, P-Value: {1}".format(tval, pval))
        sys.exit(0)

    fig, ax = plt.subplots(1, 1, figsize=(6,4))
    fig.suptitle(args.ptitle if args.ptitle else '')
    #plt.ylim(0, 1000)

    for idx, datafile in enumerate(args.datafile):
        if not os.path.exists(datafile):
            print("Datafile '{0}' does not exist" % datafile)
            return -1

        df = pd.read_csv(datafile)
        if args.print_:
            for ycol in args.ycol:
                label = "{0}:{1}".format(datafile, ycol)
                print(label, df[ycol].mean(), df[ycol].std())
            continue

        for ycol in args.ycol:   
            if args.plabel:                 label = args.plabel[idx]
            elif len(args.datafile) == 1:   label = ycol
            else:                           label = datafile

            xcol_vals = df[xcol] if xcol else df.index
            ycol_vals = df[ycol]

            if args.ptype == PlotType.line:
                ax.plot(xcol_vals, ycol_vals, label=label, color=colors[cidx], 
                    marker=markers[midx],markerfacecolor=colors[cidx])
            elif args.ptype == PlotType.scatter:
                ax.scatter(xcol_vals, ycol_vals, label=label, color=colors[cidx], 
                    marker=markers[midx])
            elif args.ptype == PlotType.bar:
                ax.bar(xcol_vals, ycol_vals, label=label, color=colors[cidx], 
                    marker=markers[midx],markerfacecolor=colors[cidx])

            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)
            ax.legend(ncol=1,loc="upper right")
            
            cidx = (cidx + 1) % len(colors)
            midx = (midx + 1) % len(markers)

    plt.savefig(args.output)
    plt.show()


if __name__ == '__main__':
    main()