#!/usr/bin/env python
import argparse
import csv
import sys
from pulp import LpInteger, LpMinimize, LpProblem, LpStatus, LpVariable

class Codelet:
    def __init__(self, name, callcount, totalcycles):
        self.fullName = name
	self.name = name.split("#")[-1]
	self.depth = self.name.count("#")
        self.callcount = callcount
        # we store cycles per iteration
        self.cycles = float(totalcycles)/callcount
        self.matching = True
        self.parents = set()
	self.add_parents(self.fullName)

    def __repr__(self):
        return self.name

    def add_parents(self, fullName):
	for parent in fullName.split("#")[:-1]:
	    self.parents.add(parent)

    def is_children_of(self, other):
        return other.name in self.parents

def parse(csvfile):
    csvreader = csv.reader(csvfile, delimiter=',')
    csvreader.next() # skip header
    codelets = {}
    for row in csvreader:
        c = Codelet(row[0], int(row[1]), int(row[2]))
        if c.name not in codelets:
	    codelets[c.name] = c
	else:
	    codelets[c.name].add_parents(c.fullName)
    
    for i in codelets.itervalues():
	yield i
    csvfile.close()

class Unsolvable(Exception):
    pass

def solve(codelets, appli_cycles, min_cycles=10**6, step=0.05,
        max_coverage=0.95, matching_file=None):

    if matching_file:
        matching_loops = [line[:-1] for line in matching_file.readlines()]

        # By default, codelets are considered matching
        for c in codelets:
            if not matches(matching_loops, c):
                c.matching = False

    coverage = max_coverage
    while(coverage > 0):
        try:
            s = list(solve_under_coverage(codelets, appli_cycles, min_cycles,
                                          coverage))
            print >>sys.stderr, "Solved with coverage >= %s" % coverage
            return s
        except Unsolvable:
            coverage = coverage - step

    print >>sys.stderr, "Solution impossible"
    sys.exit(1)

def matches(matching, c):
    for m in matching:
        if c.name.endswith(m): return True
    return False

def solve_under_coverage(codelets, appli_cycles, min_cycles=10**6,
        min_coverage=0.80):

    prob = LpProblem("granularity selection", LpMinimize)
    codelet_vars = LpVariable.dicts("codelet", 
                                    codelets, 
                                    lowBound=0, 
                                    upBound=1, 
                                    cat=LpInteger) 

    # Objective function: the codelet total cost must be minimal
    # we want small codelets
    prob += sum([codelet_vars[c]*c.cycles for c in codelets])

    # But not too small, we require at least threshold cycles for chosen 
    # codelets
    for c in codelets:
        prob += c.cycles*c.callcount >= min_cycles*codelet_vars[c]

    # and with good coverage
    prob += (sum([codelet_vars[c]*c.cycles*c.callcount for c in codelets]) 
                >= min_coverage * appli_cycles)

    # selected codelets should match
    for c in codelets:
        if not c.matching:
            prob += codelet_vars[c] == 0

    # Finally we should never include both the children and the parents
    for dad in codelets: 
        for son in codelets:
            # XXX this can be implemented much more efficiently,
            # by using the transitivity of being a parent
            if not son.is_children_of(dad): continue

            # We cannot select dad and son at the same time 
            prob += codelet_vars[dad] + codelet_vars[son] <= 1

    prob.solve()
    if (LpStatus[prob.status] != 'Optimal'):
	raise Unsolvable()
    for v in prob.variables():
        if v.varValue == 1.0:
            for c in codelets:
                if "codelet_"+c.name == v.name: 
                    yield c

    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find optimal codelet granularity")
    parser.add_argument('profile_file', type=file) 
    parser.add_argument('application_cycles', type=int)
    parser.add_argument('--min_cycles', type=int, default=10**6)
    parser.add_argument('--matching', type=file, default=None)

    args = parser.parse_args()

    codelets = list(parse(args.profile_file)) 
    for c in codelets:
       print "{}\t\t\t\t{}".format(c.name, round(c.cycles*c.callcount/args.application_cycles*100))
    chosen = solve(codelets, 
        appli_cycles=args.application_cycles,
        min_cycles=args.min_cycles,
        matching_file=args.matching)

    for c in chosen:
        print c.name