from spflow.base.structure.spn.layers.sum_layer import SPNSumLayer, marginalize
from spflow.meta.data.scope import Scope
from ..nodes.dummy_node import DummyNode
import numpy as np
import unittest


class TestLayer(unittest.TestCase):
    def test_sum_layer_initialization(self):

        # dummy children over same scope
        input_nodes = [
            DummyNode(Scope([0, 1])),
            DummyNode(Scope([0, 1])),
            DummyNode(Scope([0, 1])),
        ]

        # ----- check attributes after correct initialization -----

        l = SPNSumLayer(n_nodes=3, children=input_nodes)
        # make sure number of creates nodes is correct
        self.assertEqual(len(l.nodes), 3)
        # make sure scopes are correct
        self.assertTrue(
            np.all(
                l.scopes_out == [Scope([0, 1]), Scope([0, 1]), Scope([0, 1])]
            )
        )
        # make sure weight property works correctly
        weights = l.weights
        for node, node_weights in zip(l.nodes, weights):
            self.assertTrue(np.all(node.weights == node_weights))

        # ----- same weights for all nodes -----
        weights = np.array([[0.3, 0.3, 0.4]])

        # two dimensional weight array
        l = SPNSumLayer(n_nodes=3, children=input_nodes, weights=weights)

        for node in l.nodes:
            self.assertTrue(np.all(node.weights == weights))

        # one dimensional weight array
        l = SPNSumLayer(
            n_nodes=3, children=input_nodes, weights=weights.squeeze(0)
        )

        for node in l.nodes:
            self.assertTrue(np.all(node.weights == weights))

        # ----- different weights for all nodes -----
        weights = np.array([[0.3, 0.3, 0.4], [0.5, 0.2, 0.3], [0.1, 0.7, 0.2]])

        l = SPNSumLayer(n_nodes=3, children=input_nodes, weights=weights)

        for node, node_weights in zip(l.nodes, weights):
            self.assertTrue(np.all(node.weights == node_weights))

        # ----- two dimensional weight array of wrong shape -----
        weights = np.array([[0.3, 0.3, 0.4], [0.5, 0.2, 0.3]])

        self.assertRaises(ValueError, SPNSumLayer, 3, input_nodes, weights)
        self.assertRaises(ValueError, SPNSumLayer, 3, input_nodes, weights.T)
        self.assertRaises(
            ValueError, SPNSumLayer, 3, input_nodes, np.expand_dims(weights, 0)
        )
        self.assertRaises(
            ValueError, SPNSumLayer, 3, input_nodes, np.expand_dims(weights, -1)
        )

        # ----- incorrect number of weights -----
        weights = np.array([[0.3, 0.3, 0.3, 0.1], [0.5, 0.2, 0.2, 0.1]])
        self.assertRaises(ValueError, SPNSumLayer, 3, input_nodes, weights)

        weights = np.array([[0.3, 0.7], [0.5, 0.5]])
        self.assertRaises(ValueError, SPNSumLayer, 3, input_nodes, weights)

        # ----- weights not summing up to one per row -----
        weights = np.array([[0.3, 0.3, 0.4], [0.5, 0.7, 0.3], [0.1, 0.7, 0.2]])
        self.assertRaises(ValueError, SPNSumLayer, 3, input_nodes, weights)

        # ----- non-positive weights -----
        weights = np.array([[0.3, 0.3, 0.4], [0.5, 0.0, 0.5], [0.1, 0.7, 0.2]])
        self.assertRaises(ValueError, SPNSumLayer, 3, input_nodes, weights)

        # ----- children of different scopes -----
        input_nodes = [
            DummyNode(Scope([0, 1])),
            DummyNode(Scope([0, 1])),
            DummyNode(Scope([0])),
        ]
        self.assertRaises(ValueError, SPNSumLayer, 3, input_nodes)

        # ----- no children -----
        self.assertRaises(ValueError, SPNSumLayer, 3, [])

        # ----- invalid number of nodes -----
        self.assertRaises(ValueError, SPNSumLayer, 0, input_nodes)

    def test_sum_layer_structural_marginalization(self):

        # dummy children over same scope
        input_nodes = [
            DummyNode(Scope([0, 1])),
            DummyNode(Scope([0, 1])),
            DummyNode(Scope([0, 1])),
        ]
        l = SPNSumLayer(n_nodes=3, children=input_nodes)

        # ----- marginalize over entire scope -----
        self.assertTrue(marginalize(l, [0, 1]) == None)

        # ----- marginalize over partial scope -----
        l_marg = marginalize(
            l,
            [0],
        )
        self.assertTrue(
            l_marg.scopes_out == [Scope([1]), Scope([1]), Scope([1])]
        )
        self.assertTrue(np.all(l.weights == l_marg.weights))

        # ----- marginalize over non-scope rvs -----
        l_marg = marginalize(l, [2])

        self.assertTrue(
            l_marg.scopes_out == [Scope([0, 1]), Scope([0, 1]), Scope([0, 1])]
        )
        self.assertTrue(np.all(l.weights == l_marg.weights))


if __name__ == "__main__":
    unittest.main()