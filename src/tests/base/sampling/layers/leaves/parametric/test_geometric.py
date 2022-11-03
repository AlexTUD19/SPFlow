from spflow.meta.data import Scope
from spflow.base.structure.spn import (
    SumNode,
    ProductNode,
    Geometric,
    GeometricLayer,
)
from spflow.base.inference import log_likelihood
from spflow.base.sampling import sample
import numpy as np
import random
import unittest


class TestNode(unittest.TestCase):
    def test_sampling_1(self):

        # set seed
        np.random.seed(0)
        random.seed(0)

        geometric_layer = GeometricLayer(
            scope=Scope([0]), p=[0.8, 0.3], n_nodes=2
        )
        s1 = SumNode(children=[geometric_layer], weights=[0.3, 0.7])

        geometric_nodes = [
            Geometric(Scope([0]), p=0.8),
            Geometric(Scope([0]), p=0.3),
        ]
        s2 = SumNode(children=geometric_nodes, weights=[0.3, 0.7])

        layer_samples = sample(s1, 10000)
        nodes_samples = sample(s2, 10000)
        self.assertTrue(
            np.allclose(
                layer_samples.mean(axis=0),
                nodes_samples.mean(axis=0),
                atol=0.01,
                rtol=0.1,
            )
        )

    def test_sampling_2(self):

        # set seed
        np.random.seed(0)
        random.seed(0)

        geometric_layer = GeometricLayer(
            scope=[Scope([0]), Scope([1])], p=[0.8, 0.3]
        )
        p1 = ProductNode(children=[geometric_layer])

        geometric_nodes = [
            Geometric(Scope([0]), p=0.8),
            Geometric(Scope([1]), p=0.3),
        ]
        p2 = ProductNode(children=geometric_nodes)

        layer_samples = sample(p1, 10000)
        nodes_samples = sample(p2, 10000)
        self.assertTrue(
            np.allclose(
                layer_samples.mean(axis=0),
                nodes_samples.mean(axis=0),
                atol=0.01,
                rtol=0.1,
            )
        )

    def test_sampling_3(self):

        geometric_layer = GeometricLayer(
            scope=Scope([0]), p=[0.8, 0.3], n_nodes=2
        )

        # check if empty output ids (i.e., []) works AND sampling from non-disjoint scopes fails
        self.assertRaises(ValueError, sample, geometric_layer)


if __name__ == "__main__":
    unittest.main()
