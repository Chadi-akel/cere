#!/usr/bin/env python

from __future__ import print_function
import numpy as np
import os
import shutil
import logging
import cere_configure
import cere_instrument
import networkx as nx
import tempfile
from common.graph_utils import load_graph
import common.variables as var
import common.utils as utils

def init_module(subparsers, cere_plugins):
    cere_plugins["trace"] = run
    trace_parser = subparsers.add_parser("trace", help="produce or read a region trace")
    trace_parser.add_argument('--region', required=True, help="Region to trace")
    trace_parser.add_argument('--regions-file', help="File containing a list of regions to trace")
    trace_parser.add_argument('--norun', type=bool, const=True, default=False, nargs='?', help="instrumented binary is not automatically run")
    trace_parser.add_argument('--read', '-r', type=int, help="Read the measured cycles for given invocation (run measures if the trace is missing)")
    trace_parser.add_argument('--force', '-f', const=True, default=False, nargs='?', help="the region trace is measured even if a previous one already existed")

def parse_trace_file(tracefile):
    trace = np.fromfile(tracefile, dtype='d', count=-1)

    # filter the trace:
    # 1) odd items are cycles
    # 2) even items are invocation numbers
    size = len(trace) / 2
    return dict (cycles = trace[::2], invocations = trace[1::2],
                 size = size)

def get_region_id(region, graph):
    for n, d in graph.nodes(data=True):
        if d['_name'] == region: return n
    return None

def check_arguments(args):
    """
    Check arguments
    """

    if not (args.region or args.regions_file):
        logging.critical("No region specified, use at least one of the following: --region, --regions-file")
        return False

    if (args.regions_file and args.region):
        logging.critical("--region and --regions-file are exclusive")
        return False

    if (args.read and not args.region):
        logging.critical("--read can only be used with --region")
        return False

    if args.regions_file:
        if not os.path.isfile(args.regions_file):
            logging.critical("No such file: {0}".format(args.regions_file))
            return False
        else:
            # Make regions_file path absolute
            args.regions_file = os.path.abspath(args.regions_file)

    if args.region and utils.is_invalid(args.region):
        logging.error("{0} is invalid".format(args.region))
        return False

    return True

def find_same_level_regions(region):
    # Load graph
    graph = load_graph()
    if not graph:
        logging.error("Can't trace multiple region: Region call graph not available.\n\
                      Run cere profile.\n\
                      Tracing region {0}".format(region))
        return

    # Find region node id
    region_node = get_region_id(region, graph)

    #Find roots
    roots = [n for n,d in graph.in_degree().items() if d==0]

    #Compute for every nodes, the max distance from himself to each root
    max_path_len = {}
    for root in roots:
        for n, d in graph.nodes(data=True):
            if n not in max_path_len: max_path_len[n]=0
            #Get every paths from the current root to the node
            paths = list(nx.all_simple_paths(graph, root, n))
            #Keep the max length path
            for path in paths:
                if len(path)-1 > max_path_len[n]:
                    max_path_len[n] = len(path)-1

    #Keep region which have the same depth than the requested region
    for n, p in max_path_len.iteritems():
        if p == max_path_len[region_node]:
            yield graph.node[n]['_name']

def find_regions_to_trace(args):
    regions_to_trace = set()

    # If user passed a regions_file, read regions from it
    if args.regions_file:
        with file(args.regions_file) as f:
            for line in f.readlines():
                # Trim line
                line = line.trim()
                # Ignore commented lines
                if not line.startswith('#'):
                    regions_to_trace.add(line)

    # If user passed a single region
    elif args.region:
        regions_to_trace.add(args.region)

        # If multiple trace is on when using single region, add sibbling
        # regions to the list of regions_to_trace
        if cere_configure.cere_config["multiple_trace"]:
            for same_level in find_same_level_regions(args.region):
                regions_to_trace.add(same_level)

    return regions_to_trace

def need_to_measure(region):
    if utils.is_invalid(region):
        return False

    if utils.trace_exists(region):
        return False

    return True

def launch_trace(args, regions):
    with tempfile.NamedTemporaryFile() as temp:
        for region in regions:
            temp.write(region + '\n')
        temp.flush()

        args.regions_file = temp.name
        args.invocation = 0
        args.wrapper = var.RDTSC_WRAPPER
        args.force = True

        os.environ["CERE_TRACE"] = "1"
        result = cere_instrument.run(args)
        del os.environ["CERE_TRACE"]
        return result

def run(args):
    cere_configure.init()

    if not check_arguments(args):
        return False

    # Find loops to trace
    regions = find_regions_to_trace(args)

    # When force is off, filter already measured regions
    if not args.force:
        regions = [r for r in regions if need_to_measure(r)]

    result = True

    # Are there any regions to trace ?
    if len(regions) == 0:
        logging.info("No regions to trace")
    else:
        result = launch_trace(args, regions)

    # Move trace files to cere_measures
    if not args.norun:
        for region in regions:
            try:
                shutil.move("{0}.bin".format(region), cere_configure.cere_config["cere_measures_path"])
                shutil.move("{0}.csv".format(region), cere_configure.cere_config["cere_measures_path"])
            except IOError as err:
                logging.critical(str(err))
                logging.critical("Trace failed for region {0}: No output files, maybe the selected region does not exist.".format(region))
                utils.mark_invalid(region)
                result = False

    # If read is used, read given invocation from trace file
    if args.read and utils.trace_exists(args.region):
        base_name = "{0}/{1}".format(cere_configure.cere_config["cere_measures_path"], args.region)
        trace = parse_trace_file(base_name + '.bin')
        cycles = int(trace['cycles'][trace['invocations'] == args.read])
        print(cycles)

    return result
