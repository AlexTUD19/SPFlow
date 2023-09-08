import random
import unittest

import numpy as np
import torch
import tensorly as tl

from spflow.meta.data import Scope
from spflow.meta.dispatch import SamplingContext
from spflow.torch.sampling import sample
from spflow.tensorly.sampling import sample
#from spflow.torch.structure.spn import Gamma
from spflow.tensorly.structure.general.nodes.leaves.parametric.general_gamma import Gamma
from spflow.torch.structure.general.nodes.leaves.parametric.gamma import updateBackend
from spflow.tensorly.utils.helper_functions import tl_toNumpy, tl_isnan


class TestGamma(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        torch.set_default_dtype(torch.float64)

    @classmethod
    def teardown_class(cls):
        torch.set_default_dtype(torch.float32)

    def test_sampling_1(self):

        # set seed
        torch.manual_seed(0)
        np.random.seed(0)
        random.seed(0)

        # ----- alpha = 1, beta = 1 -----

        gamma = Gamma(Scope([0]), 1.0, 1.0)

        data = torch.tensor([[float("nan")], [float("nan")], [float("nan")]])

        samples = sample(gamma, data, sampling_ctx=SamplingContext([0, 2]))

        self.assertTrue(all(samples.isnan() == torch.tensor([[False], [True], [False]])))

        samples = sample(gamma, 1000)
        self.assertTrue(torch.isclose(samples.mean(), torch.tensor(1.0 / 1.0), rtol=0.1))

    def test_sampling_2(self):

        # set seed
        torch.manual_seed(0)
        np.random.seed(0)
        random.seed(0)

        # ----- alpha = 0.5, beta = 1.5 -----

        gamma = Gamma(Scope([0]), 0.5, 1.5)

        samples = sample(gamma, 1000)
        self.assertTrue(torch.isclose(samples.mean(), torch.tensor(0.5 / 1.5), rtol=0.1))

    def test_sampling_3(self):

        # set seed
        torch.manual_seed(0)
        np.random.seed(0)
        random.seed(0)

        # ----- alpha = 1.5, beta = 0.5 -----

        gamma = Gamma(Scope([0]), 1.5, 0.5)

        samples = sample(gamma, 1000)
        self.assertTrue(torch.isclose(samples.mean(), torch.tensor(1.5 / 0.5), rtol=0.1))

    def test_update_backend(self):
        backends = ["numpy", "pytorch"]
        # set seed
        torch.manual_seed(0)
        np.random.seed(0)
        random.seed(0)

        # ----- alpha = 1, beta = 1 -----

        gamma = Gamma(Scope([0]), 1.0, 1.0)

        data = torch.tensor([[float("nan")], [float("nan")], [float("nan")]])

        samples = sample(gamma, data, sampling_ctx=SamplingContext([0, 2]))
        notNans = samples[~tl_isnan(samples)]

        # make sure that probabilities match python backend probabilities
        for backend in backends:
            tl.set_backend(backend)
            gamma_updated = updateBackend(gamma)
            samples_updated = sample(gamma_updated, tl.tensor(data, dtype=tl.float64), sampling_ctx=SamplingContext([0, 2]))
            # check conversion from torch to python
            self.assertTrue(all(tl_isnan(samples) == tl_isnan(samples_updated)))
            self.assertTrue(all(tl_toNumpy(notNans) == tl_toNumpy(samples_updated[~tl_isnan(samples_updated)])))



if __name__ == "__main__":
    torch.set_default_dtype(torch.float64)
    unittest.main()
