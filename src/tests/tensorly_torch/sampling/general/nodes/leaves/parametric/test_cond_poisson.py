import random
import unittest

import numpy as np
import torch
import tensorly as tl

from spflow.meta.data import Scope
from spflow.meta.dispatch import SamplingContext
from spflow.tensorly.sampling import sample
from spflow.tensorly.structure.general.nodes.leaves.parametric.general_cond_poisson import CondPoisson
from spflow.torch.structure.general.nodes.leaves.parametric.cond_poisson import updateBackend
from spflow.tensorly.utils.helper_functions import tl_toNumpy, tl_isnan

tc = unittest.TestCase()

def test_sampling_1(do_for_all_backends):

    # set seed
    torch.manual_seed(0)
    np.random.seed(0)
    random.seed(0)

    # ----- l = 1.0 -----

    poisson = CondPoisson(Scope([0], [1]), cond_f=lambda data: {"l": 1.0})
    data = tl.tensor([[float("nan")], [float("nan")], [float("nan")]], dtype=tl.float64)

    samples = sample(poisson, data, sampling_ctx=SamplingContext([0, 2]))

    tc.assertTrue(all(tl_isnan(samples) == tl.tensor([[False], [True], [False]])))

    samples = sample(poisson, 1000)
    tc.assertTrue(np.isclose(samples.mean(), tl.tensor(1.0), rtol=0.1))

def test_sampling_2(do_for_all_backends):

    # set seed
    torch.manual_seed(0)
    np.random.seed(0)
    random.seed(0)

    # ----- l = 0.5 -----

    poisson = CondPoisson(Scope([0], [1]), cond_f=lambda data: {"l": 0.5})

    samples = sample(poisson, 1000)
    tc.assertTrue(np.isclose(samples.mean(), tl.tensor(0.5), rtol=0.1))

def test_sampling_3(do_for_all_backends):

    # set seed
    torch.manual_seed(0)
    np.random.seed(0)
    random.seed(0)

    # ----- l = 2.5 -----

    poisson = CondPoisson(Scope([0], [1]), cond_f=lambda data: {"l": 2.5})

    samples = sample(poisson, 1000)
    tc.assertTrue(np.isclose(tl.mean(samples), tl.tensor(2.5), rtol=0.1))

def test_update_backend(do_for_all_backends):
    backends = ["numpy", "pytorch"]
    # set seed
    torch.manual_seed(0)
    np.random.seed(0)
    random.seed(0)

    # ----- l = 1.0 -----

    poisson = CondPoisson(Scope([0], [1]), cond_f=lambda data: {"l": 1.0})
    data = tl.tensor([[float("nan")], [float("nan")], [float("nan")]], dtype=tl.float64)

    samples = sample(poisson, data, sampling_ctx=SamplingContext([0, 2]))
    notNans = samples[~tl_isnan(samples)]

    # make sure that probabilities match python backend probabilities
    for backend in backends:
        with tl.backend_context(backend):
            poisson_updated = updateBackend(poisson)
            samples_updated = sample(poisson_updated, tl.tensor(data, dtype=tl.float64), sampling_ctx=SamplingContext([0, 2]))
            # check conversion from torch to python
            tc.assertTrue(all(tl_isnan(samples) == tl_isnan(samples_updated)))
            tc.assertTrue(all(tl_toNumpy(notNans) == tl_toNumpy(samples_updated[~tl_isnan(samples_updated)])))



if __name__ == "__main__":
    torch.set_default_dtype(torch.float64)
    unittest.main()
