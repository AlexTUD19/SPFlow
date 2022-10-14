from spflow.meta.scope.scope import Scope
from spflow.base.structure.layers.leaves.parametric.exponential import ExponentialLayer
from spflow.base.learning.layers.leaves.parametric.exponential import maximum_likelihood_estimation

import numpy as np
import unittest
import random


class TestNode(unittest.TestCase):
    def test_mle(self):

        # set seed
        np.random.seed(0)
        random.seed(0)
        
        layer = ExponentialLayer(scope=[Scope([0]), Scope([1])])

        # simulate data
        data = np.hstack([np.random.exponential(scale=1.0/0.3, size=(20000, 1)), np.random.exponential(scale=1.0/2.7, size=(20000, 1))])

        # perform MLE
        maximum_likelihood_estimation(layer, data)

        self.assertTrue(np.allclose(layer.l, np.array([0.3, 2.7]), atol=1e-2, rtol=1e-2))


if __name__ == "__main__":
    unittest.main()