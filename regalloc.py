#!/usr/bin/env python3

__doc__ = '''Register allocation pass, using the linear-scan algorithm.
Assumes that all temporaries can be allocated to any register (because of this,
it does not work with non integer types).'''

from cfg import *

# the register of all spilled temporaries is set to SPILL_FLAG
SPILL_FLAG = 999


class minimal_register_allocator(object):

    def __init__(self, cfg, nregs):
        self.cfg = cfg
        self.nregs = nregs
        self.allocresult = RegisterAllocation(dict(), 0, self.nregs)

    def __call__(self):
        blockq = list(self.cfg.heads().values())
        i = 0
        while i < len(blockq):
            n = blockq[i].succ()
            nreal = []
            for b in n:
                if not (b in blockq):
                    nreal.append(b)
            blockq += nreal

            bbra = bb_register_allocator(blockq[i], self.nregs)
            thisalloc = bbra()
            print("block:", repr(id(blockq[i])))
            print("varliveness:\n", repr(bbra.varliveness))
            print("ralloc:\n", repr(thisalloc), "\n")
            self.allocresult.update(thisalloc)
            i += 1

        return self.allocresult


class RegisterAllocation(object):
    '''Object that contains the information about where each temporary is
    allocated.

    Spill handling is done by reserving 2 machine registers to be filled
    as late as possible, and spilled again as soon as possible. This class is
    responsible for filling these registers.'''

    def __init__(self, vartoreg, numspill, nregs):
        self.vartoreg = vartoreg
        self.numspill = numspill
        self.nregs = nregs
        self.vartospillframeoffset = dict()
        self.spillregi = 0
        self.spillframeoffseti = 0

    def update(self, otherra):
        self.vartoreg.update(otherra.vartoreg)
        self.numspill += otherra.numspill

    def spill_room(self):
        return self.numspill * 4

    def dematerialize_spilled_var_if_necessary(self, var):
        '''Resets the register used for a spill variable when we know that instance
        of the variable is now dead.'''
        if self.vartoreg[var] >= self.nregs - 2:
            self.vartoreg[var] = SPILL_FLAG

    def materialize_spilled_var_if_necessary(self, var):
        '''Decide which of the spill-reserved registers to fill with a spilled
        variable. Also, decides to which stack location the variable is spilled
        to, the first time this method is called for that variable.

        Returns True iff the variable was spilled in the register
        allocation phase.

        The algorithm used to decide which register is filled is simple: the
        register chosen is the one that was not chosen the last time. It always
        works and it never needs any information about which registers are live
        at a given time.'''

        if self.vartoreg[var] != SPILL_FLAG:
            # already allocated and filled! nothing to do
            if self.vartoreg[var] >= self.nregs - 2:
                return True
            return False

        # decide the register
        self.vartoreg[var] = self.spillregi + self.nregs - 2
        self.spillregi = (self.spillregi + 1) % 2

        # decide the location in the current frame
        if not (var in self.vartospillframeoffset):
            self.vartospillframeoffset[var] = self.spillframeoffseti
            self.spillframeoffseti += 4
        return True

    def __repr__(self):
        return 'vartoreg = ' + repr(self.vartoreg)


class bb_register_allocator(object):

    def __init__(self, bb, nregs, prevralloc=None):
        self.bb = bb
        self.nregs = nregs

        self.vartoreg = {}
        # when the same variable is used across more than one basic block, the other
        # basic blocks should inherit the register where the variable was
        # previously allocated
        # yet to be implemented because currently it can never happen
        if prevralloc:
            livein = bb.live_in
            for livevar in livein:
                if prevralloc[livevar]:
                    self.vartoreg[livevar] = prevralloc[livevar]
                    raise Exception("register inheritance not fully implemented")

        # liveness of a variable on entry to each instruction
        # in order of start point
        self.varliveness = []  # {var=var, liveness=[indexes]}

        self.allvars = bb.live_in.union(bb.live_out)
        self.allvars = self.allvars.union(bb.gen.union(bb.kill))
        self.allvars = remove_non_regs(self.allvars)
        self.allvars = list(self.allvars)

    def compute_liveness_intervals(self):
        '''Simplified one-pass liveness analysis, for a single basic block.
        It can be done in one pass because in a single basic block there are
        no branches.'''
        vartolasti = dict()
        livevars = set()
        i = len(self.bb.instrs) - 1

        while i >= 0:
            inst = self.bb.instrs[i]
            kills = remove_non_regs(inst.collect_kills())
            uses = remove_non_regs(inst.collect_uses())
            livevars -= kills
            livevars |= uses

            for var in kills:
                lasti = vartolasti.get(var)
                if lasti:
                    self.varliveness.insert(0, {"var": var, "interv": lasti})

            for var in livevars:
                lasti = vartolasti.get(var)
                if lasti is None:
                    lasti = []
                lasti.insert(0, i)
                vartolasti[var] = lasti

            i -= 1

        for var in livevars:
            lasti = vartolasti[var]
            if lasti:
                self.varliveness.insert(0, {"var": var, "interv": lasti})

    def __call__(self):
        '''Linear-scan register allocation (a variant of the more general
        graph coloring algorithm known as "left-edge")'''

        self.compute_liveness_intervals()

        live = []
        freeregs = set(range(0, self.nregs - 2))  # -2 for spill room
        numspill = 0

        for livei in self.varliveness:
            start = livei["interv"][0]

            # expire old intervals
            i = 0
            while i < len(live):
                notlivecandidate = live[i]
                if notlivecandidate["interv"][-1] < start:
                    live.pop(i)
                    freeregs.add(self.vartoreg[notlivecandidate["var"]])
                i += 1

            if len(freeregs) == 0:
                tospill = live[-1]
                # keep the longest interval
                if tospill["interv"][-1] > livei["interv"][-1]:
                    # we have to spill "tospill"
                    self.vartoreg[livei["var"]] = self.vartoreg[tospill["var"]]
                    self.vartoreg[tospill["var"]] = SPILL_FLAG
                    live.pop(-1)  # remove spill from active
                    live.append(livei)  # add i to active
                else:
                    self.vartoreg[livei["var"]] = SPILL_FLAG
                numspill += 1

            else:
                self.vartoreg[livei["var"]] = freeregs.pop()
                live.append(livei)

            # sort the active intervals by increasing end point
            live.sort(key=lambda li: li['interv'][-1])

        return RegisterAllocation(self.vartoreg, numspill, self.nregs)
