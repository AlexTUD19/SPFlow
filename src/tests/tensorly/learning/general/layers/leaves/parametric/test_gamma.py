import random
import unittest

import numpy as np
import tensorly as tl
from spflow.tensorly.utils.helper_functions import tl_allclose, tl_vstack

from spflow.tensorly.learning import maximum_likelihood_estimation
from spflow.tensorly.structure.spn import GammaLayer
from spflow.meta.data import Scope


class TestNode(unittest.TestCase):
    def test_mle(self):

        # set seed
        np.random.seed(0)
        random.seed(0)

        layer = GammaLayer(scope=[Scope([0]), Scope([1])])

        # simulate data
        data = np.hstack(
            [
                np.random.gamma(shape=0.3, scale=1.0 / 1.7, size=(30000, 1)),
                np.random.gamma(shape=1.9, scale=1.0 / 0.7, size=(30000, 1)),
            ]
        )

        # perform MLE
        maximum_likelihood_estimation(layer, data)

        self.assertTrue(tl_allclose(layer.alpha, tl.tensor([0.3, 1.9]), atol=1e-2, rtol=1e-2))
        self.assertTrue(tl_allclose(layer.beta, tl.tensor([1.7, 0.7]), atol=1e-2, rtol=1e-2))

    def test_weighted_mle(self):

        leaf = GammaLayer([Scope([0]), Scope([1])])

        data = np.hstack(
            [
                tl_vstack(
                    [
                        np.random.gamma(shape=1.7, scale=1.0 / 0.8, size=(10000, 1)),
                        np.random.gamma(shape=0.5, scale=1.0 / 1.4, size=(10000, 1)),
                    ]
                ),
                tl_vstack(
                    [
                        np.random.gamma(shape=0.9, scale=1.0 / 0.3, size=(10000, 1)),
                        np.random.gamma(shape=1.3, scale=1.0 / 1.7, size=(10000, 1)),
                    ]
                ),
            ]
        )
        weights = tl.concatenate([tl.zeros(10000), tl.ones(10000)])

        maximum_likelihood_estimation(leaf, data, weights)

        self.assertTrue(tl_allclose(leaf.alpha, tl.tensor([0.5, 1.3]), atol=1e-2, rtol=1e-2))
        self.assertTrue(tl_allclose(leaf.beta, tl.tensor([1.4, 1.7]), atol=1e-2, rtol=1e-2))


if __name__ == "__main__":
    unittest.main()
