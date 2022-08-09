from spflow.meta.scope.scope import Scope
from spflow.meta.contexts.sampling_context import SamplingContext
from spflow.base.structure.nodes.leaves.parametric.negative_binomial import NegativeBinomial
from spflow.base.sampling.nodes.leaves.parametric.negative_binomial import sample
from spflow.base.sampling.module import sample

import numpy as np

import unittest


class TestNegativeBinomial(unittest.TestCase):
    def test_sampling_1(self):

        # ----- n = 1, p = 1.0 -----

        negative_binomial = NegativeBinomial(Scope([0]), 1, 1.0)
        data = np.array([[np.nan], [np.nan], [np.nan]])

        samples = sample(negative_binomial, data, sampling_ctx=SamplingContext([0, 2]))

        self.assertTrue(all(np.isnan(samples) == np.array([[False], [True], [False]])))
        self.assertTrue(all(samples[~np.isnan(samples)] == 0.0))

    def test_sampling_2(self):

        # ----- n = 10, p = 0.3 -----

        negative_binomial = NegativeBinomial(Scope([0]), 10, 0.3)

        samples = sample(negative_binomial, 1000)
        self.assertTrue(np.isclose(samples.mean(), np.array(10 * (1 - 0.3) / 0.3), rtol=0.1))

    def test_sampling_3(self):

        # ----- n = 5, p = 0.8 -----

        negative_binomial = NegativeBinomial(Scope([0]), 5, 0.8)

        samples = sample(negative_binomial, 1000)
        self.assertTrue(np.isclose(samples.mean(), np.array(5 * (1 - 0.8) / 0.8), rtol=0.1))


if __name__ == "__main__":
    unittest.main()