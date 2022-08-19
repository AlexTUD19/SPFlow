from spflow.meta.scope.scope import Scope
from spflow.base.structure.layers.leaves.parametric.poisson import PoissonLayer
from spflow.base.inference.layers.leaves.parametric.poisson import log_likelihood
from spflow.base.sampling.layers.leaves.parametric.poisson import sample
from spflow.base.structure.nodes.node import SPNSumNode, SPNProductNode
from spflow.base.inference.nodes.node import log_likelihood
from spflow.base.sampling.nodes.node import sample
from spflow.base.structure.nodes.leaves.parametric.poisson import Poisson
from spflow.base.inference.nodes.leaves.parametric.poisson import log_likelihood
from spflow.base.sampling.nodes.leaves.parametric.poisson import sample
from spflow.base.inference.module import log_likelihood
from spflow.base.sampling.module import sample

import numpy as np
import unittest


class TestNode(unittest.TestCase):
    def test_sampling_1(self):

        poisson_layer = PoissonLayer(scope=Scope([0]), l=[0.8, 0.3], n_nodes=2)
        s1 = SPNSumNode(children=[poisson_layer], weights=[0.3, 0.7])

        poisson_nodes = [Poisson(Scope([0]), l=0.8), Poisson(Scope([0]), l=0.3)]
        s2 = SPNSumNode(children=poisson_nodes, weights=[0.3, 0.7])

        layer_samples = sample(s1, 10000)
        nodes_samples = sample(s2, 10000)
        self.assertTrue(np.allclose(layer_samples.mean(axis=0), nodes_samples.mean(axis=0), atol=0.01, rtol=0.1))

    def test_sampling_2(self):

        poisson_layer = PoissonLayer(scope=[Scope([0]), Scope([1])], l=[0.8, 0.3])
        p1 = SPNProductNode(children=[poisson_layer])

        poisson_nodes = [Poisson(Scope([0]), l=0.8), Poisson(Scope([1]), l=0.3)]
        p2 = SPNProductNode(children=poisson_nodes)

        layer_samples = sample(p1, 10000)
        nodes_samples = sample(p2, 10000)
        self.assertTrue(np.allclose(layer_samples.mean(axis=0), nodes_samples.mean(axis=0), atol=0.01, rtol=0.1))


if __name__ == "__main__":
    unittest.main()