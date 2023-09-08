import random
import unittest

import numpy as np
import torch
import tensorly as tl

from spflow.meta.data import Scope
from spflow.meta.dispatch import SamplingContext
from spflow.torch.sampling import sample
from spflow.tensorly.sampling import sample
#from spflow.torch.structure.spn import CondPoisson
from spflow.tensorly.structure.general.nodes.leaves.parametric.general_cond_poisson import CondPoisson
from spflow.torch.structure.general.nodes.leaves.parametric.cond_poisson import updateBackend
from spflow.tensorly.utils.helper_functions import tl_toNumpy, tl_isnan


class TestPoisson(unittest.TestCase):
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

        # ----- l = 1.0 -----

        poisson = CondPoisson(Scope([0], [1]), cond_f=lambda data: {"l": 1.0})
        data = torch.tensor([[float("nan")], [float("nan")], [float("nan")]])

        samples = sample(poisson, data, sampling_ctx=SamplingContext([0, 2]))

        self.assertTrue(all(samples.isnan() == torch.tensor([[False], [True], [False]])))

        samples = sample(poisson, 1000)
        self.assertTrue(torch.isclose(samples.mean(), torch.tensor(1.0), rtol=0.1))

    def test_sampling_2(self):

        # set seed
        torch.manual_seed(0)
        np.random.seed(0)
        random.seed(0)

        # ----- l = 0.5 -----

        poisson = CondPoisson(Scope([0], [1]), cond_f=lambda data: {"l": 0.5})

        samples = sample(poisson, 1000)
        self.assertTrue(torch.isclose(samples.mean(), torch.tensor(0.5), rtol=0.1))

    def test_sampling_3(self):

        # set seed
        torch.manual_seed(0)
        np.random.seed(0)
        random.seed(0)

        # ----- l = 2.5 -----

        poisson = CondPoisson(Scope([0], [1]), cond_f=lambda data: {"l": 2.5})

        samples = sample(poisson, 1000)
        self.assertTrue(torch.isclose(samples.mean(), torch.tensor(2.5), rtol=0.1))

    def test_update_backend(self):
        backends = ["numpy", "pytorch"]
        # set seed
        torch.manual_seed(0)
        np.random.seed(0)
        random.seed(0)

        # ----- l = 1.0 -----

        poisson = CondPoisson(Scope([0], [1]), cond_f=lambda data: {"l": 1.0})
        data = torch.tensor([[float("nan")], [float("nan")], [float("nan")]])

        samples = sample(poisson, data, sampling_ctx=SamplingContext([0, 2]))
        notNans = samples[~tl_isnan(samples)]

        # make sure that probabilities match python backend probabilities
        for backend in backends:
            tl.set_backend(backend)
            poisson_updated = updateBackend(poisson)
            samples_updated = sample(poisson_updated, tl.tensor(data, dtype=tl.float32), sampling_ctx=SamplingContext([0, 2]))
            # check conversion from torch to python
            self.assertTrue(all(tl_isnan(samples) == tl_isnan(samples_updated)))
            self.assertTrue(all(tl_toNumpy(notNans) == tl_toNumpy(samples_updated[~tl_isnan(samples_updated)])))



if __name__ == "__main__":
    torch.set_default_dtype(torch.float64)
    unittest.main()
