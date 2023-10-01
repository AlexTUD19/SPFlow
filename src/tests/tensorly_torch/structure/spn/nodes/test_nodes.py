import unittest

import numpy as np
import torch
import tensorly as tl

from spflow.meta.data import Scope
from spflow.tensorly.structure.spn import ProductNode, SumNode
from spflow.tensorly.structure import marginalize
from spflow.tensorly.structure.general.nodes.leaves.parametric.general_gaussian import Gaussian
from spflow.tensorly.structure.spn.nodes.product_node import updateBackend
from spflow.tensorly.utils.helper_functions import tl_toNumpy

from ...general.nodes.dummy_node import DummyNode

tc = unittest.TestCase()

def test_sum_node_initialization(do_for_all_backends):

    # empty children
    tc.assertRaises(ValueError, SumNode, [], [])
    # non-Module children
    tc.assertRaises(ValueError, SumNode, [DummyNode(Scope([0])), 0], [0.5, 0.5])
    # children with different scopes
    tc.assertRaises(
        ValueError,
        SumNode,
        [DummyNode(Scope([0])), DummyNode(Scope([1]))],
        [0.5, 0.5],
    )
    # number of child outputs not matching number of weights
    tc.assertRaises(
        ValueError,
        SumNode,
        [DummyNode(Scope([0])), DummyNode(Scope([0]))],
        [1.0],
    )
    # non-positive weights
    tc.assertRaises(ValueError, SumNode, [DummyNode(Scope([0]))], [0.0])
    # weights not summing up to one
    tc.assertRaises(
        ValueError,
        SumNode,
        [DummyNode(Scope([0])), DummyNode(Scope([0]))],
        [0.3, 0.5],
    )
    # weights of invalid shape
    tc.assertRaises(ValueError, SumNode, [DummyNode(Scope([0]))], [[1.0]])

    # weights as list of floats
    SumNode([DummyNode(Scope([0])), DummyNode(Scope([0]))], tl.tensor([0.5, 0.5]))
    # weights as numpy array
    SumNode([DummyNode(Scope([0])), DummyNode(Scope([0]))], tl.tensor(np.array([0.5, 0.5])))
    # weights as torch tensor
    SumNode(
        [DummyNode(Scope([0])), DummyNode(Scope([0]))],
        tl.tensor(tl.tensor([0.5, 0.5])),
    )
    # no weights
    SumNode([DummyNode(Scope([0])), DummyNode(Scope([0]))])

def test_sum_node_marginalization_1(do_for_all_backends):

    s = SumNode([DummyNode(Scope([0])), DummyNode(Scope([0]))])

    s_marg = marginalize(s, [1])
    tc.assertEqual(s_marg.scopes_out, s.scopes_out)

    s_marg = marginalize(s, [0])
    tc.assertEqual(s_marg, None)

def test_sum_node_marginalization_2(do_for_all_backends):

    s = SumNode(
        [
            ProductNode([DummyNode(Scope([0])), DummyNode(Scope([1]))]),
            ProductNode([DummyNode(Scope([0])), DummyNode(Scope([1]))]),
        ]
    )

    s_marg = marginalize(s, [0])
    tc.assertEqual(s_marg.scopes_out, [Scope([1])])

    s_marg = marginalize(s, [1])
    tc.assertEqual(s_marg.scopes_out, [Scope([0])])

    s_marg = marginalize(s, [0, 1])
    tc.assertEqual(s_marg, None)

def test_product_node_initialization(do_for_all_backends):

    # empty children
    tc.assertRaises(ValueError, ProductNode, [])
    # non-Module children
    tc.assertRaises(ValueError, ProductNode, [DummyNode(Scope([0])), 0])
    # children with non-disjoint scopes
    tc.assertRaises(
        ValueError,
        ProductNode,
        [DummyNode(Scope([0])), DummyNode(Scope([0]))],
    )

    ProductNode([DummyNode(Scope([0])), DummyNode(Scope([1]))])

def test_product_node_marginalization_1(do_for_all_backends):

    p = ProductNode([DummyNode(Scope([0])), DummyNode(Scope([1]))])

    p_marg = marginalize(p, [2])
    tc.assertEqual(p_marg.scopes_out, p.scopes_out)

    p_marg = marginalize(p, [1], prune=False)
    tc.assertEqual(p_marg.scopes_out, [Scope([0])])

    p_marg = marginalize(p, [1], prune=True)
    # pruning should return single child directly
    tc.assertTrue(isinstance(p_marg, DummyNode))

def test_product_node_marginalization_2(do_for_all_backends):

    p = ProductNode(
        [
            ProductNode([DummyNode(Scope([0])), DummyNode(Scope([1]))]),
            ProductNode([DummyNode(Scope([2])), DummyNode(Scope([3]))]),
        ]
    )

    p_marg = marginalize(p, [2])
    tc.assertEqual(p_marg.scopes_out, [Scope([0, 1, 3])])

def test_update_backend(do_for_all_backends):
    backends = ["numpy", "pytorch"]
    weights_1: np.array = np.random.rand(2)
    weights_1 /= weights_1.sum()

    weights_2: np.array = np.random.rand(1)
    weights_2 /= weights_2.sum()

    # INode graph
    graph = ProductNode(
        [
            SumNode(
                [Gaussian(Scope([0])), Gaussian(Scope([0]))],
                weights=tl.tensor(weights_1),
            ),
            SumNode([Gaussian(Scope([1]))], weights=tl.tensor(weights_2)),
        ]
    )
    p_out = graph.scopes_out
    s1_out = graph.children[0].scopes_out
    s2_out = graph.children[1].scopes_out
    for backend in backends:
        with tl.backend_context(backend):
            graph_updated = updateBackend(graph)
            p_out_updated = graph_updated.scopes_out
            s1_out_updated = graph_updated.children[0].scopes_out
            s2_out_updated = graph_updated.children[1].scopes_out
            tc.assertTrue(p_out == p_out_updated)
            tc.assertTrue(s1_out == s1_out_updated)
            tc.assertTrue(s2_out == s2_out_updated)
            # check conversion from torch to python
            weights_1_up = graph.children[0].weights
            weights_2_up = graph.children[1].weights
            tc.assertTrue(
                np.allclose(
                    weights_1,
                    tl_toNumpy(weights_1_up)
                )
            )
            tc.assertTrue(
                np.allclose(
                    weights_2,
                    tl_toNumpy(weights_2_up)
                )
            )

if __name__ == "__main__":
    unittest.main()
