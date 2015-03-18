#!/usr/bin/env python

import networkx as nx
import cPickle as pickle
import logging
import os
import subprocess
import cere_configure

def plot(g, step):
    import os
    for n,d in g.nodes(data=True):
        d["label"]="{} {} {} ({})".format(n, d['_name'], d['_self_coverage'], d['_coverage'])
        if not d['_valid'] or d['_small']: d["style"]="dotted"
        else: d["style"]="solid"
        if d['_tested']:
            d["style"]="solid"
            if not d['_matching']: d['color']="red"
            else: d['color']="green"
        if d['_to_test']: d['color']="orange"
    for u,v,d in g.edges(data=True):
        d["label"] = d["weight"]
    logging.info("Plot graph_{0}.pdf".format(step))
    nx.write_dot(g,"{0}/graph_{1}.dot".format(cere_configure.cere_config["cere_measures_path"], step))
    try:
        logging.info(subprocess.check_output("dot -Tpdf {0}/graph_{1}.dot -o {0}/graph_{1}.pdf".format(cere_configure.cere_config["cere_measures_path"], step), stderr=subprocess.STDOUT, shell=True))
    except subprocess.CalledProcessError as err:
        logging.info("Canno't create the pdf")
        logging.info(str(err))
        logging.info(err.output)

def load_graph(step=""):
    logging.info('Loading graph...')
    if not os.path.isfile("{0}/graph_{1}.pkl".format(cere_configure.cere_config["cere_measures_path"], step)): return None
    with open("{0}/graph_{1}.pkl".format(cere_configure.cere_config["cere_measures_path"], step), 'rb') as input:
        graph = pickle.load(input)
    return graph

def save_graph(g, step=""):
    logging.info('Saving graph...')
    with open("{0}/graph_{1}.pkl".format(cere_configure.cere_config["cere_measures_path"], step), 'wb') as output:
        pickle.dump(g, output, pickle.HIGHEST_PROTOCOL)
    logging.info('Saving done')
