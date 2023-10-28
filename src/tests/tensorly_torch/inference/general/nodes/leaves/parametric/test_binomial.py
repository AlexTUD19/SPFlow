import random
import unittest

import numpy as np
import torch
import tensorly as tl

from spflow.tensorly.structure.spn import Binomial
from spflow.meta.data import Scope
from spflow.tensorly.inference import likelihood, log_likelihood
from spflow.base.structure.general.nodes.leaves.parametric.binomial import Binomial as BaseBinomial
from spflow.torch.structure.general.nodes.leaves.parametric.binomial import updateBackend
from spflow.tensorly.utils.helper_functions import tl_toNumpy, tl_unsqueeze

tc = unittest.TestCase()

def test_inference(do_for_all_backends):

    n = random.randint(2, 10)
    p = random.random()

    binomial = Binomial(Scope([0]), n, p)
    node_binomial = BaseBinomial(Scope([0]), n, p)

    # create dummy input data (batch size x random variables)
    data = np.random.randint(1, n, (3, 1))

    log_probs = log_likelihood(node_binomial, data)
    log_probs_torch = log_likelihood(binomial, tl.tensor(data))

    # make sure that probabilities match python backend probabilities
    tc.assertTrue(np.allclose(log_probs, tl_toNumpy(log_probs_torch)))

def test_gradient_computation(do_for_all_backends):

    if do_for_all_backends == "numpy":
        return

    n = random.randint(2, 10)
    p = random.random()

    binomial = Binomial(Scope([0]), n, p)

    # create dummy input data (batch size x random variables)
    data = np.random.randint(1, n, (3, 1))

    log_probs_torch = log_likelihood(binomial, tl.tensor(data))

    # create dummy targets
    targets_torch = torch.ones(3, 1)

    loss = torch.nn.MSELoss()(log_probs_torch, targets_torch)
    loss.backward()

    tc.assertTrue(binomial.n.grad is None)
    tc.assertTrue(binomial.p_aux.grad is not None)

    n_orig = binomial.n.detach().clone()
    p_aux_orig = binomial.p_aux.detach().clone()

    optimizer = torch.optim.SGD(binomial.parameters(), lr=1)
    optimizer.step()

    # make sure that parameters are correctly updated
    tc.assertTrue(torch.allclose(n_orig, binomial.n))
    tc.assertTrue(torch.allclose(p_aux_orig - binomial.p_aux.grad, binomial.p_aux))

    # verify that distribution parameters match parameters
    tc.assertTrue(torch.equal(binomial.n, binomial.dist.total_count.long()))
    tc.assertTrue(torch.allclose(binomial.p, binomial.dist.probs))

def test_gradient_optimization(do_for_all_backends):

    if do_for_all_backends == "numpy":
        return

    torch.manual_seed(0)

    # initialize distribution
    binomial = Binomial(Scope([0]), 5, 0.3)

    # create dummy data
    p_target = 0.8
    data = torch.distributions.Binomial(5, p_target).sample((100000, 1))

    # initialize gradient optimizer
    optimizer = torch.optim.SGD(binomial.parameters(), lr=0.5)

    # perform optimization (possibly overfitting)
    for i in range(40):

        # clear gradients
        optimizer.zero_grad()

        # compute negative log-likelihood
        nll = -log_likelihood(binomial, data).mean()
        nll.backward()

        # update parameters
        optimizer.step()

    tc.assertTrue(torch.allclose(binomial.p, tl.tensor(p_target, dtype=tl.float64), atol=1e-3, rtol=1e-3))

def test_likelihood_p_0(do_for_all_backends):
    torch.set_default_dtype(torch.float64)

    # p = 0
    binomial = Binomial(Scope([0]), 1, 0.0)

    data = tl.tensor([[0.0], [1.0]])
    targets = tl.tensor([[1.0], [0.0]])

    probs = likelihood(binomial, data)
    log_probs = log_likelihood(binomial, data)

    tc.assertTrue(np.allclose(tl_toNumpy(probs), tl_toNumpy(tl.exp(log_probs))))
    tc.assertTrue(np.allclose(tl_toNumpy(probs), targets))

def test_likelihood_p_1(do_for_all_backends):

    # p = 1
    binomial = Binomial(Scope([0]), 1, 1.0)

    data = tl.tensor([[0.0], [1.0]])
    targets = tl.tensor([[0.0], [1.0]])

    probs = likelihood(binomial, data)
    log_probs = log_likelihood(binomial, data)

    tc.assertTrue(np.allclose(tl_toNumpy(probs), tl_toNumpy(tl.exp(log_probs))))
    tc.assertTrue(np.allclose(tl_toNumpy(probs), targets))

def test_likelihood_n_0(do_for_all_backends):

    # n = 0
    binomial = Binomial(Scope([0]), 0, 0.5)

    data = tl.tensor([[0.0]])
    targets = tl.tensor([[1.0]])

    probs = likelihood(binomial, data)
    log_probs = log_likelihood(binomial, data)

    tc.assertTrue(np.allclose(tl_toNumpy(probs), tl_toNumpy(tl.exp(log_probs))))
    tc.assertTrue(np.allclose(tl_toNumpy(probs), targets))

def test_likelihood_marginalization(do_for_all_backends):

    binomial = Binomial(Scope([0]), 5, 0.5)
    data = tl.tensor([[float("nan")]])

    # should not raise and error and should return 1 (0 in log-space)
    probs = likelihood(binomial, data)

    tc.assertTrue(np.allclose(tl_toNumpy(probs), tl.tensor(1.0)))

def test_support(do_for_all_backends):

    # Support for Binomial distribution: integers {0,...,n}

    binomial = Binomial(Scope([0]), 2, 0.5)

    # check infinite values
    tc.assertRaises(ValueError, log_likelihood, binomial, tl.tensor([[-np.inf]]))
    tc.assertRaises(ValueError, log_likelihood, binomial, tl.tensor([[np.inf]]))

    # check valid integers inside valid range
    log_likelihood(
        binomial,
        tl_unsqueeze(tl.tensor(list(range(binomial.n + 1))), 1),
    )

    # check valid integers, but outside of valid range
    tc.assertRaises(ValueError, log_likelihood, binomial, tl.tensor([[-1]]))
    tc.assertRaises(
        ValueError,
        log_likelihood,
        binomial,
        tl.tensor([[float(binomial.n + 1)]]),
    )

    # check invalid float values
    tc.assertRaises(
        ValueError,
        log_likelihood,
        binomial,
        tl.tensor([[np.nextafter(tl.tensor(0.0), tl.tensor(-1.0))]]),
    )
    tc.assertRaises(
        ValueError,
        log_likelihood,
        binomial,
        tl.tensor([[np.nextafter(tl.tensor(0.0), tl.tensor(1.0))]]),
    )
    tc.assertRaises(
        ValueError,
        log_likelihood,
        binomial,
        tl.tensor(
            [
                [
                    np.nextafter(
                        tl.tensor(float(binomial.n)),
                        tl.tensor(float(binomial.n + 1)),
                    )
                ]
            ]
        ),
    )
    tc.assertRaises(
        ValueError,
        log_likelihood,
        binomial,
        tl.tensor([[np.nextafter(tl.tensor(float(binomial.n)), tl.tensor(0.0))]]),
    )
    tc.assertRaises(ValueError, log_likelihood, binomial, tl.tensor([[0.5]]))
    tc.assertRaises(ValueError, log_likelihood, binomial, tl.tensor([[3.5]]))

def test_update_backend(do_for_all_backends):
    backends = ["numpy", "pytorch"]
    p = random.random()

    n = random.randint(2, 10)
    p = random.random()

    binomial = Binomial(Scope([0]), n, p)

    # create dummy input data (batch size x random variables)
    data = np.random.randint(0, 2, (3, 1))

    log_probs = log_likelihood(binomial, tl.tensor(data))

    # make sure that probabilities match python backend probabilities
    for backend in backends:
        with tl.backend_context(backend):
            binomial_updated = updateBackend(binomial)
            log_probs_updated = log_likelihood(binomial_updated, tl.tensor(data))
            # check conversion from torch to python
            tc.assertTrue(np.allclose(tl_toNumpy(log_probs), tl_toNumpy(log_probs_updated)))


if __name__ == "__main__":
    torch.set_default_dtype(torch.float64)
    unittest.main()
