import random
import unittest

import numpy as np

from spflow.base.sampling import sample
from spflow.base.structure.spn import Poisson
from spflow.meta.data import Scope
from spflow.meta.dispatch import SamplingContext


class TestPoisson(unittest.TestCase):
    def test_sampling_1(self):

        # set seed
        np.random.seed(0)
        random.seed(0)

        # ----- l = 1.0 -----

        poisson = Poisson(Scope([0]), 1.0)
        data = np.array([[np.nan], [np.nan], [np.nan]])

        samples = sample(poisson, data, sampling_ctx=SamplingContext([0, 2]))

        self.assertTrue(
            all(np.isnan(samples) == np.array([[False], [True], [False]]))
        )

        samples = sample(poisson, 1000)
        self.assertTrue(np.isclose(samples.mean(), np.array(1.0), rtol=0.1))

    def test_sampling_2(self):

        # set seed
        np.random.seed(0)
        random.seed(0)

        # ----- l = 0.5 -----

        poisson = Poisson(Scope([0]), 0.5)

        samples = sample(poisson, 1000)
        self.assertTrue(np.isclose(samples.mean(), np.array(0.5), rtol=0.1))

    def test_sampling_3(self):

        # set seed
        np.random.seed(0)
        random.seed(0)

        # ----- l = 2.5 -----

        poisson = Poisson(Scope([0]), 2.5)

        samples = sample(poisson, 1000)
        self.assertTrue(np.isclose(samples.mean(), np.array(2.5), rtol=0.1))

    def test_sampling_4(self):

        poisson = Poisson(Scope([0]), 2.5)

        # make sure that instance ids out of bounds raise errors
        self.assertRaises(
            ValueError,
            sample,
            poisson,
            np.array([[0]]),
            sampling_ctx=SamplingContext([1]),
        )


if __name__ == "__main__":
    unittest.main()
