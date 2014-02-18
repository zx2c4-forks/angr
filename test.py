#!/usr/bin/env python

import nose
import logging
l = logging.getLogger("simuvex.test")

try:
	# pylint: disable=W0611
	import standard_logging
	import angr_debug
except ImportError:
	pass

import symexec
#import simuvex
from simuvex.s_memory import SimMemory, Vectorizer
from simuvex import SimValue, ConcretizingException, SimState

# pylint: disable=R0904
def test_memory():
	initial_memory = { 0: 'A', 1: 'A', 2: 'A', 3: 'A', 10: 'B' }
	vectorized_memory = Vectorizer(initial_memory)
	mem = SimMemory(backer=vectorized_memory)

	# concrete address and concrete result
	addr = SimValue(symexec.BitVecVal(0, 64))
	loaded,_ = mem.load(addr, 4) # Returns: a z3 BitVec representing 0x41414141
	loaded_val = mem.load_val(addr, 4) # Returns: a z3 BitVec representing 0x41414141
	nose.tools.assert_false(loaded_val.is_symbolic())
	nose.tools.assert_equal(loaded, loaded_val.expr)
	nose.tools.assert_equal(loaded_val.any(), 0x41414141)

	# concrete address and partially symbolic result
	addr = SimValue(symexec.BitVecVal(2, 64))
	loaded_val = mem.load_val(addr, 4)
	nose.tools.assert_true(loaded_val.is_symbolic())
	nose.tools.assert_greater_equal(loaded_val.any(), 0x41410000)
	nose.tools.assert_less_equal(loaded_val.any(), 0x41420000)
	nose.tools.assert_equal(loaded_val.min(), 0x41410000)
	nose.tools.assert_equal(loaded_val.max(), 0x4141ffff)

	# symbolic (but fixed) address and concrete result
	x = symexec.BitVec('x', 64)
	addr = SimValue(x, constraints = [ x == 10 ])
	loaded_val = mem.load_val(addr, 1)
	nose.tools.assert_false(loaded_val.is_symbolic())
	nose.tools.assert_equal(loaded_val.any(), 0x42)

def test_symvalue():
	# concrete symvalue
	zero = SimValue(symexec.BitVecVal(0, 64))
	nose.tools.assert_false(zero.is_symbolic())
	nose.tools.assert_equal(zero.any(), 0)
	nose.tools.assert_raises(ConcretizingException, zero.exactly_n, 2)

	# symbolic symvalue
	x = symexec.BitVec('x', 64)
	sym = SimValue(x, constraints = [ x > 100, x < 200 ])
	nose.tools.assert_true(sym.is_symbolic())
	nose.tools.assert_equal(sym.min(), 101)
	nose.tools.assert_equal(sym.max(), 199)
	nose.tools.assert_items_equal(sym.any_n(99), range(101, 200))
	nose.tools.assert_raises(ConcretizingException, zero.exactly_n, 102)

def test_state_merge():
	a = SimState()
	a.store_mem(1, symexec.BitVecVal(42, 8))

	b = a.copy_exact()
	c = b.copy_exact()
	a.store_mem(2, a.mem_expr(1, 1)+1)
	b.store_mem(2, b.mem_expr(1, 1)*2)
	c.store_mem(2, c.mem_expr(1, 1)/2)

	# make sure the byte at 1 is right
	nose.tools.assert_equal(a.mem_value(1, 1).any(), 42)
	nose.tools.assert_equal(b.mem_value(1, 1).any(), 42)
	nose.tools.assert_equal(c.mem_value(1, 1).any(), 42)

	# make sure the byte at 2 is right
	nose.tools.assert_equal(a.mem_value(2, 1).any(), 43)
	nose.tools.assert_equal(b.mem_value(2, 1).any(), 84)
	nose.tools.assert_equal(c.mem_value(2, 1).any(), 21)

	# the byte at 2 should be unique for all before the merge
	nose.tools.assert_true(a.mem_value(2, 1).is_unique())
	nose.tools.assert_true(b.mem_value(2, 1).is_unique())
	nose.tools.assert_true(c.mem_value(2, 1).is_unique())

	merge_val = a.merge(b, c)

	# the byte at 2 should now *not* be unique for a
	nose.tools.assert_false(a.mem_value(2, 1).is_unique())
	nose.tools.assert_true(b.mem_value(2, 1).is_unique())
	nose.tools.assert_true(c.mem_value(2, 1).is_unique())

	# the byte at 2 should have the three values
	nose.tools.assert_items_equal(a.mem_value(2, 1).any_n(10), (43, 84, 21))

	# we should be able to select them by adding constraints
	a_a = a.copy_exact()
	a_a.add_constraints(merge_val == 0)
	nose.tools.assert_true(a_a.mem_value(2, 1).is_unique())
	nose.tools.assert_equal(a_a.mem_value(2, 1).any(), 43)

	a_b = a.copy_exact()
	a_b.add_constraints(merge_val == 1)
	nose.tools.assert_true(a_b.mem_value(2, 1).is_unique())
	nose.tools.assert_equal(a_b.mem_value(2, 1).any(), 84)

	a_c = a.copy_exact()
	a_c.add_constraints(merge_val == 2)
	nose.tools.assert_true(a_c.mem_value(2, 1).is_unique())
	nose.tools.assert_equal(a_c.mem_value(2, 1).any(), 21)

if __name__ == '__main__':
	test_state_merge()
