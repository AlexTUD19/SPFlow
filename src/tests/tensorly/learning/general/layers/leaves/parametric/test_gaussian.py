import random
import unittest

import numpy as np
import tensorly as tl
from spflow.tensorly.utils.helper_functions import tl_allclose, tl_vstack

from spflow.tensorly.learning import maximum_likelihood_estimation
from spflow.tensorly.structure.spn import GaussianLayer
from spflow.meta.data import Scope


class TestNode(unittest.TestCase):
    def test_mle(self):

        # set seed
        np.random.seed(0)
        random.seed(0)

        layer = GaussianLayer(scope=[Scope([0]), Scope([1])])

        # simulate data
        data = np.hstack(
            [
                np.random.normal(loc=-1.7, scale=0.2, size=(20000, 1)),
                np.random.normal(loc=0.5, scale=1.3, size=(20000, 1)),
            ]
        )

        # perform MLE
        maximum_likelihood_estimation(layer, data)

        self.assertTrue(tl_allclose(layer.mean, tl.tensor([-1.7, 0.5]), atol=1e-2, rtol=1e-2))
        self.assertTrue(tl_allclose(layer.std, tl.tensor([0.2, 1.3]), atol=1e-2, rtol=1e-2))

    def test_weighted_mle(self):

        leaf = GaussianLayer([Scope([0]), Scope([1])])

        data = np.hstack(
            [
                tl_vstack(
                    [
                        np.random.normal(1.7, 0.8, size=(10000, 1)),
                        np.random.normal(0.5, 1.4, size=(10000, 1)),
                    ]
                ),
                tl_vstack(
                    [
                        np.random.normal(0.9, 0.3, size=(10000, 1)),
                        np.random.normal(1.3, 1.7, size=(10000, 1)),
                    ]
                ),
            ]
        )
        weights = tl.concatenate([tl.zeros(10000), tl.ones(10000)])

        maximum_likelihood_estimation(leaf, data, weights)

        self.assertTrue(tl_allclose(leaf.mean, tl.tensor([0.5, 1.3]), atol=1e-2, rtol=1e-1))
        self.assertTrue(tl_allclose(leaf.std, tl.tensor([1.4, 1.7]), atol=1e-2, rtol=1e-1))


if __name__ == "__main__":
    unittest.main()
