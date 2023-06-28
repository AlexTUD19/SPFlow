import random
import unittest

import numpy as np
import tensorly as tl
from spflow.tensorly.utils.helper_functions import tl_allclose, tl_isclose

from spflow.tensorly.inference import log_likelihood
from spflow.tensorly.sampling import sample
from spflow.tensorly.structure.spn import ProductNode, SumNode
from spflow.tensorly.structure.general.nodes.leaves import Gaussian
#from spflow.tensorly.structure.general.nodes.leaves.parametric.general_gaussian import GeneralGaussian as Gaussian
from spflow.meta.data import Scope


class TestNode(unittest.TestCase):
    def test_spn_sampling(self):

        # set seed
        np.random.seed(0)
        random.seed(0)

        s = SumNode(
            children=[
                SumNode(
                    children=[
                        ProductNode(
                            children=[
                                Gaussian(Scope([0]), -7.0, 1.0),
                                Gaussian(Scope([1]), 7.0, 1.0),
                            ],
                        ),
                        ProductNode(
                            children=[
                                Gaussian(Scope([0]), -5.0, 1.0),
                                Gaussian(Scope([1]), 5.0, 1.0),
                            ],
                        ),
                    ],
                    weights=[0.2, 0.8],
                ),
                SumNode(
                    children=[
                        ProductNode(
                            children=[
                                Gaussian(Scope([0]), -3.0, 1.0),
                                Gaussian(Scope([1]), 3.0, 1.0),
                            ],
                        ),
                        ProductNode(
                            children=[
                                Gaussian(Scope([0]), -1.0, 1.0),
                                Gaussian(Scope([1]), 1.0, 1.0),
                            ],
                        ),
                    ],
                    weights=[0.6, 0.4],
                ),
            ],
            weights=[0.7, 0.3],
        )

        samples = sample(s, 1000)
        expected_mean = 0.7 * (0.2 * tl.tensor([-7, 7]) + 0.8 * tl.tensor([-5, 5])) + 0.3 * (
            0.6 * tl.tensor([-3, 3]) + 0.4 * tl.tensor([-1, 1])
        )

        self.assertTrue(tl_allclose(samples.mean(axis=0), expected_mean, rtol=0.1))

    def test_sum_node_sampling(self):

        # set seed
        np.random.seed(0)
        random.seed(0)

        l1 = Gaussian(Scope([0]), -5.0, 1.0)
        l2 = Gaussian(Scope([0]), 5.0, 1.0)

        # ----- weights 0, 1 -----

        s = SumNode([l1, l2], weights=[0.001, 0.999])

        samples = sample(s, 1000)
        self.assertTrue(tl_isclose(samples.mean(), tl.tensor(5.0), rtol=0.1))

        # ----- weights 1, 0 -----

        s = SumNode([l1, l2], weights=[0.999, 0.001])

        samples = sample(s, 1000)
        self.assertTrue(tl_isclose(samples.mean(), tl.tensor(-5.0), rtol=0.1))

        # ----- weights 0.2, 0.8 -----

        s = SumNode([l1, l2], weights=[0.2, 0.8])

        samples = sample(s, 1000)
        self.assertTrue(tl_isclose(samples.mean(), tl.tensor(3.0), rtol=0.1))


if __name__ == "__main__":
    unittest.main()
