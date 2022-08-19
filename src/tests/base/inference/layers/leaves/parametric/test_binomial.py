from spflow.meta.scope.scope import Scope
from spflow.meta.contexts.dispatch_context import DispatchContext
from spflow.base.structure.layers.leaves.parametric.binomial import BinomialLayer
from spflow.base.inference.layers.leaves.parametric.binomial import log_likelihood
from spflow.base.structure.nodes.leaves.parametric.binomial import Binomial
from spflow.base.inference.nodes.leaves.parametric.binomial import log_likelihood
from spflow.base.structure.nodes.node import SPNProductNode, SPNSumNode
from spflow.base.inference.nodes.node import log_likelihood
from spflow.base.inference.module import log_likelihood
import numpy as np
import unittest


class TestNode(unittest.TestCase):
    def test_layer_likelihood_1(self):

        binomial_layer = BinomialLayer(scope=[Scope([0]), Scope([0])], n=3, p=[0.8, 0.3])
        s1 = SPNSumNode(children=[binomial_layer], weights=[0.3, 0.7])

        binomial_nodes = [Binomial(Scope([0]), n=3, p=0.8), Binomial(Scope([0]), n=3, p=0.3)]
        s2 = SPNSumNode(children=binomial_nodes, weights=[0.3, 0.7])

        data = np.array([[0], [1], [0]])

        self.assertTrue(np.all(log_likelihood(s1, data) == log_likelihood(s2, data)))
    
    def test_layer_likelihood_2(self):

        binomial_layer = BinomialLayer(scope=[Scope([0]), Scope([1])], n=[3, 5], p=[0.8, 0.3])
        p1 = SPNProductNode(children=[binomial_layer])

        binomial_nodes = [Binomial(Scope([0]), n=3, p=0.8), Binomial(Scope([1]), n=5, p=0.3)]
        p2 = SPNProductNode(children=binomial_nodes)

        data = np.array([[0, 1], [1, 1], [0, 0]])

        self.assertTrue(np.all(log_likelihood(p1, data) == log_likelihood(p2, data)))


if __name__ == "__main__":
    unittest.main()