import unittest

import tensorly as tl

from spflow.tensorly.inference import log_likelihood
from spflow.tensorly.structure.spn import (
    ProductNode,
    SumNode,
)
from spflow.tensorly.utils.helper_functions import tl_allclose
from spflow.tensorly.structure.general.nodes.leaves import Exponential
from spflow.tensorly.structure.general.layers.leaves import ExponentialLayer
from spflow.meta.data import Scope


class TestNode(unittest.TestCase):
    def test_layer_likelihood_1(self):

        exponential_layer = ExponentialLayer(scope=Scope([0]), l=[0.8, 0.3], n_nodes=2)
        s1 = SumNode(children=[exponential_layer], weights=[0.3, 0.7])

        exponential_nodes = [
            Exponential(Scope([0]), l=0.8),
            Exponential(Scope([0]), l=0.3),
        ]
        s2 = SumNode(children=exponential_nodes, weights=[0.3, 0.7])

        data = tl.tensor([[0.5], [1.5], [0.3]])

        self.assertTrue(tl_allclose(log_likelihood(s1, data), log_likelihood(s2, data)))

    def test_layer_likelihood_2(self):

        exponential_layer = ExponentialLayer(scope=[Scope([0]), Scope([1])], l=[0.8, 0.3])
        p1 = ProductNode(children=[exponential_layer])

        exponential_nodes = [
            Exponential(Scope([0]), l=0.8),
            Exponential(Scope([1]), l=0.3),
        ]
        p2 = ProductNode(children=exponential_nodes)

        data = tl.tensor([[0.5, 1.6], [0.1, 0.3], [0.47, 0.7]])

        self.assertTrue(tl_allclose(log_likelihood(p1, data), log_likelihood(p2, data)))


if __name__ == "__main__":
    unittest.main()
