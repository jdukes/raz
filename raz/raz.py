#!/usr/bin/env python
#This is a niave redos checker.. it may get smarter
#What the fuck is opcode 8? it's not in the fucking source...
#_sre expects good input..

from random import randint
import sre_parse
from sre_constants import *
from itertools import chain, combinations


###############################################################################
# Constants
###############################################################################

LEAF_NAMES = ["literal",
              "range",
              "not_literal",
              "not_literal_ignore",
              "at"]
LEAF_NAMES.extend(sre_constants.CHCODES.keys())

KLEEN_LOWER_BOUND = 1024 #play with this number
REPEAT_NODES = 2
REPEAT_MAX_COUNT = 1
SUBPATTERN_NODES = 1

###############################################################################
# Exceptions
###############################################################################


class ErrorUnparseable(Exception):
    
    def __init__(self, value):
        self.value = value
        
    def __str__(self):
        repr(self.value)


###############################################################################
# Primary Class
###############################################################################


class RegexAnalyzer:
    
    def __init__(self, pattern, flags=0):
        self.pattern = pattern
        try:
            self.parsed_pattern = sre_parse.parse(pattern, flags)
        except error, e:
            raise ErrorUnparseable(
                'Invalid regex %s failed: %s' % (pattern,e.message))
        self.rtree = ReNode(self.parsed_pattern)
        self._analyze(self.rtree)
        
    def _analyze(self, rtree):
        #there must be an x, y, and z such that x enters the regex,
        #there are multiple matches for y that point back to root, and
        #z does not match.
        for node in rtree:
            if node.ntype == 'branch':
                if node.kleene_enuf_node:
                    node.parent.tainted = True
        for node in rtree:
            if node.tainted:
                for p1,p2 in combinations(node.get_paths(), 2):
                    if p1.overalps(p2):
                        node.evil = True
                    
        
    def check_is_evil(self):
        return any( node.evil for node in self.rtree)


###############################################################################
# helper classes
###############################################################################


class ReNode:

    def __init__(self, parsed_pattern, parent=None):
        self.pattern = parsed_pattern
        self.children = []
        self.depth = 0
        self.evil = False
        self.tainted = False
        self.parent = parent
        if parent:
            self.depth = self.parent.depth+1
        self.ntype = None #unit test make sure this is set
        #v-make sure this works with unit testing
        if self.pattern.__class__ == sre_parse.SubPattern:
            #ensure that all children are tuples
            self.ntype = "root"
            if self.pattern:
                for node in self.pattern:
                    self.children.append(ReNode(node, self))
        else:
            self.op, self.arg = self.pattern
            if self.op in LEAF_NAMES:
                self.make_leaf()
            else:
                self.make_branch()

    def __iter__(self):
        yield self
        if self.children:
            for c in self.children:
                for i in chain(sc for sc in c):
                    yield i

    def __repr__(self):
        prefix = '\t' * self.depth
        if self.ntype in ['root','branch']:
            if self.ntype == 'branch' and self.kleene_enuf_node:
                prefix += "Kleen "
            text = prefix + "ReNode %s " % (self.ntype)
            if self.children:
                text += "with children:\n" 
                text += '\n'.join(repr(c) for c in self.children)
            return text
        else:
            return "%sleaf with pattern: %s" % (prefix, 
                                                str(self.pattern))

    def make_leaf(self):
        self.ntype = "leaf"
        self.match_set = set()
        if self.op == "literal":
            self.match_set = set([self.arg])
        if self.op == "range":
            start, end = self.arg
            self.match_set = set(range(start, end+1))

    def make_branch(self):
        self.ntype = "branch"
        self.kleene_enuf_node = False
        if self.op == "max_repeat":
            if self.arg[REPEAT_MAX_COUNT] > KLEEN_LOWER_BOUND: 
                self.kleene_enuf_node = True
            for node in self.arg[REPEAT_NODES]:
                self.children.append(ReNode(node, self))
        if self.op == "subpattern":
            for node in self.arg[SUBPATTERN_NODES]:
                self.children.append(ReNode(node, self))
        if self.op == "in":
            for node in self.arg:
                self.children.append(ReNode(node, self))
    
    def get_paths(self):
        return (RePath(c) for c in self.children)


class RePath:

    def __init__(self, node):
        self.node = node
    
    def overlaps(self, other_path):
        pass


#CHCODES <- category codes
#OPCODES <- all operations, sub on these


# 

# (a+)+
# ([a-zA-Z]+)*
# (a|aa)+
# (a|a?)+
# (.*a){11}
# ^([a-zA-Z0-9])(([\-.]|[_]+)?([a-zA-Z0-9]+))*(@){1}[a-z0-9]+[.]{1}(([a-z]{2,3})|([a-z]{2,3}[.]{1}[a-z]{2,3}))$
# ^(([a-z])+.)+[A-Z]([a-z])+$

        
    
#not evil
# ([^a]*a){x,}.
