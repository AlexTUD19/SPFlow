import unittest

import tensorly as tl
from spflow.tensorly.utils.helper_functions import tl_allclose
from spflow.tensorly.inference import log_likelihood
from spflow.tensorly.structure.spn import ProductNode, SumNode
from spflow.tensorly.structure.general.nodes.leaves import Binomial
from spflow.tensorly.structure.general.layers.leaves import BinomialLayer
from spflow.meta.data import Scope


class TestNode(unittest.TestCase):
    def test_layer_likelihood_1(self):

        binomial_layer = BinomialLayer(scope=[Scope([0]), Scope([0])], n=3, p=[0.8, 0.3])
        s1 = SumNode(children=[binomial_layer], weights=[0.3, 0.7])

        binomial_nodes = [
            Binomial(Scope([0]), n=3, p=0.8),
            Binomial(Scope([0]), n=3, p=0.3),
        ]
        s2 = SumNode(children=binomial_nodes, weights=[0.3, 0.7])

        data = tl.tensor([[0], [1], [0]])

        self.assertTrue(tl_allclose(log_likelihood(s1, data), log_likelihood(s2, data)))

    def test_layer_likelihood_2(self):

        binomial_layer = BinomialLayer(scope=[Scope([0]), Scope([1])], n=[3, 5], p=[0.8, 0.3])
        p1 = ProductNode(children=[binomial_layer])

        binomial_nodes = [
            Binomial(Scope([0]), n=3, p=0.8),
            Binomial(Scope([1]), n=5, p=0.3),
        ]
        p2 = ProductNode(children=binomial_nodes)

        data = tl.tensor([[0, 1], [1, 1], [0, 0]])

        self.assertTrue(tl_allclose(log_likelihood(p1, data), log_likelihood(p2, data)))


if __name__ == "__main__":
    unittest.main()
