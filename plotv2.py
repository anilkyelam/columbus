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
import numpy as np
from enum import Enum
import scipy.stats as scstats


colors = ['r','b','g','brown', 'c','k', 'orange', 'm','orangered']
linetypes = ['g-','g--','g-+']
markers = ['x','+','o','s','+', '|', '^']

class PlotType(Enum):
    line = 'line'
    scatter = 'scatter'
    bar = 'bar'
    cdf = 'cdf'

    def __str__(self):
        return self.value


def gen_cdf(npArray, num_bin):
   x = np.sort(npArray)
   y = 1. * np.arange(len(npArray)) / (len(npArray) - 1)
#    h, edges = np.histogram(array, density=True, bins=num_bin )
#    h = np.cumsum(h)/np.cumsum(h).max()
#    x = edges.repeat(2)[:-1]
#    y = np.zeros_like(x)
#    y[1:] = h.repeat(2)
   return x, y


# Argument Parser
def parse_args():
    parser = argparse.ArgumentParser("Python Generic Plotter")

    parser.add_argument('-d', '--datafile', 
        action='append', 
        help='path to the data file, multiple values are allowed')
        
    parser.add_argument('-xc', '--xcol', 
        action='store', 
        help='X column  from csv file. Defaults to row index if not provided.', 
        required=False)

    parser.add_argument('-yc', '--ycol', 
        action='append', 
        help='Y column from csv file, multiple values are allowed')

    parser.add_argument('-dxc', '--dfilexcol', 
        nargs=2,
        action='store', 
        help='X column  from a specific csv file. Defaults to row index if not provided.', 
        required=False)

    parser.add_argument('-dyc', '--dfileycol',
        nargs=2,
        action='append',
        metavar=('datafile', 'ycol'),
        help='Y column from a specific file that is included with this argument')

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

    parser.add_argument('-xl', '--xlabel', 
        action='store', 
        help='Custom x-axis label')

    parser.add_argument('-yl', '--ylabel', 
        action='store', 
        help='Custom y-axis label')

    parser.add_argument('-xm', '--xmul', 
        action='store', 
        type=float,
        help='Custom x-axis multiplier constant (e.g., to change units)',
        default=1)

    parser.add_argument('-ym', '--ymul', 
        action='store', 
        type=float,
        help='Custom y-axis multiplier constant (e.g., to change units)',
        default=1)

    parser.add_argument('--xlog', 
        action='store_true', 
        help='Plot x-axis on log scale',
        default=False)
        
    parser.add_argument('--ylog', 
        action='store_true', 
        help='Plot y-axis on log scale',
        default=False)

    parser.add_argument('-l', '--plabel', 
        action='append', 
        help='plot label, can provide one label per ycol or datafile')

    parser.add_argument('-nm', '--nomarker',  
        action='store_true', 
        help='dont add markers to plots', 
        default=False)

    parser.add_argument('-nt', '--notail',  
        action='store', 
        help='eliminate last x% tail from CDF. Defaults to 1%', 
        nargs='?',
        type=float,
        const=1.0)

    parser.add_argument('-nh', '--nohead',  
        action='store', 
        help='eliminate first x% head from CDF. Defaults to 1%', 
        nargs='?',
        type=float,
        const=1.0)

    parser.add_argument('-s', '--show',  
        action='store_true', 
        help='Display the plot after saving it. Blocks the program.', 
        default=False)

    args = parser.parse_args()
    return args


def main():
    args = parse_args()

    # Plot can be: 
    # 1. One datafile with multiple ycolumns plotted against single xcolumn
    # 2. Single ycolumn from multiple datafiles plotted against an xcolumn
    # 3. If ycols from multiple datafiles must be plotted, use -dyc argument style
    dyc=(args.dfileycol is not None)
    dandyc=(args.datafile is not None or args.ycol is not None)
    if (dyc and dandyc) or not (dyc or dandyc):
        print("Use either the (-dyc) or the (-d and -yc) approach - atleast one, and not both!")
        return -1

    if (args.datafile or args.ycol) and \
        (args.datafile and len(args.datafile) > 1) and \
        (args.ycol and len(args.ycol) > 1):
        print("Only one of datafile or ycolumn arguments can provide multiple values. Use -dyc style if this doesn't work for you.")
        return -1

    # Get files, xcols and ycols from args
    num_plots = 0
    dfile_xcol = None
    dfile_ycol_map = []     #Maintain the input order
    if args.dfileycol:
        dfilexcol = args.dfilexcol
        for (dfile, ycol) in args.dfileycol:
            if args.xcol and not dfile_xcol:
                dfile_xcol = (dfile, args.xcol)
            dfile_ycol_map.append((dfile, ycol))
            num_plots += 1
    else:
        for dfile in args.datafile:
            if args.xcol and not dfile_xcol:
                dfile_xcol = (dfile, args.xcol)
            for ycol in args.ycol:
                dfile_ycol_map.append((dfile, ycol))
                num_plots += 1

    if args.plabel and len(args.plabel) != num_plots:
        print("If plot labels are provided, they must be provided for all the plots and are mapped one-to-one in input order")
        return -1

    xlabel = args.xlabel if args.xlabel else args.xcol
    ylabel = args.ylabel if args.ylabel else args.ycol

    cidx = 0
    midx = 0
    lidx = 0
    aidx = 0

    font = {'family' : 'sans',
            'size'   : 15}
    matplotlib.rc('font', **font)
    matplotlib.rc('figure', autolayout=True)

    fig, ax = plt.subplots(1, 1, figsize=(8,5))
    fig.suptitle(args.ptitle if args.ptitle else '')
    #plt.ylim(0, 1000)

    if args.xlog:
        ax.set_xscale('log')
    if args.ylog:
        ax.set_yscale('log')

    xcol = None
    if dfile_xcol:
        df = pd.read_csv(dfile_xcol[0])
        xcol = df[dfile_xcol[1]]

    plot_num = 0
    for (datafile, ycol) in dfile_ycol_map:

        if not os.path.exists(datafile):
            print("Datafile {0} does not exist".format(datafile))
            return -1

        df = pd.read_csv(datafile)
        if args.print_:
            for ycol in ycols:
                label = "{0}:{1}".format(datafile, ycol)
                print(label, df[ycol].mean(), df[ycol].std())
            continue
 
        if args.plabel:                 label = args.plabel[plot_num]
        elif len(args.datafile) == 1:   label = ycol
        else:                           label = datafile

        if xcol is None:
            xcol = df.index

        if args.ptype == PlotType.line:
            xc = xcol
            yc = df[ycol]
            xc = [x * args.xmul for x in xc]
            yc = [y * args.ymul for y in yc]

            if args.nomarker:
                ax.plot(xc, yc, label=label, color=colors[cidx])
            else:
                ax.plot(xc, yc, label=label, color=colors[cidx], 
                    marker=markers[midx],markerfacecolor=colors[cidx])

        elif args.ptype == PlotType.scatter:
            xc = xcol
            yc = df[ycol]
            xc = [x * args.xmul for x in xc]
            yc = [y * args.ymul for y in yc]

            if args.nomarker:
                ax.scatter(xc, yc, label=label, color=colors[cidx])
            else:
                ax.scatter(xc, yc, label=label, color=colors[cidx], 
                    marker=markers[midx])

        elif args.ptype == PlotType.bar:
            xc = xcol
            yc = df[ycol]
            xc = [x * args.xmul for x in xc]
            yc = [y * args.ymul for y in yc]

            if args.nomarker:
                ax.bar(xc, yc, label=label, color=colors[cidx])
            else:
                ax.bar(xc, yc, label=label, color=colors[cidx], 
                    marker=markers[midx],markerfacecolor=colors[cidx])

        elif args.ptype == PlotType.cdf:
            xc, yc = gen_cdf(df[ycol], 100000)

            head = 0
            tail = len(xc)
            if args.nohead:
                for i, val in enumerate(yc):
                    if val <= args.nohead/100.0:
                        head = i
            if args.notail:
                for i, val in enumerate(yc):
                    if val > (100.0 - args.notail)/100.0:
                        tail = i
                        break

            for i, val in enumerate(yc):
                if val > 0.99:
                    idx = i
                    break

            xc = xc[head:tail]
            yc = yc[head:tail]
            xc = [x * args.xmul for x in xc]
            yc = [y * args.ymul for y in yc]

            if args.nomarker:
                ax.plot(xc, yc, label=label, color=colors[cidx])
            else:
                ax.plot(xc, yc, label=label, color=colors[cidx],
                    marker=markers[midx],markerfacecolor=colors[cidx])

            ylabel = "CDF"
            

        #ax.set_xlim(0, 1000000)
        #ax.set_ylim(0, 25)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        # ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.05), ncol=3, fancybox=True, shadow=True)
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), ncol=1, fancybox=True, shadow=True)
        
        cidx = (cidx + 1) % len(colors)
        midx = (midx + 1) % len(markers)
        plot_num += 1

    plt.savefig(args.output, format="eps")
    if args.show:
        plt.show()

if __name__ == '__main__':
    main()