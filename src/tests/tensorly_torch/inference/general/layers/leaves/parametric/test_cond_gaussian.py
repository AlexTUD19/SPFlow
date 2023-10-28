import random
import unittest

import torch
import tensorly as tl
import numpy as np

from spflow.meta.data import Scope
from spflow.meta.dispatch import DispatchContext
from spflow.tensorly.inference import likelihood, log_likelihood
from spflow.tensorly.structure.general.layers.leaves.parametric.general_cond_gaussian import CondGaussianLayer
from spflow.tensorly.structure.general.nodes.leaves.parametric.general_cond_gaussian import CondGaussian
from spflow.torch.structure.general.layers.leaves.parametric.cond_gaussian import updateBackend
from spflow.tensorly.utils.helper_functions import tl_toNumpy

tc = unittest.TestCase()

def test_likelihood_no_mean(do_for_all_backends):

    gaussian = CondGaussianLayer(Scope([0], [1]), cond_f=lambda data: {"std": [1.0, 1.0]}, n_nodes=2)
    tc.assertRaises(KeyError, log_likelihood, gaussian, tl.tensor([[0], [1]]))

def test_likelihood_no_std(do_for_all_backends):

    gaussian = CondGaussianLayer(Scope([0], [1]), cond_f=lambda data: {"mean": [0.0, 0.0]}, n_nodes=2)
    tc.assertRaises(KeyError, log_likelihood, gaussian, tl.tensor([[0], [1]]))

def test_likelihood_no_mean_std(do_for_all_backends):

    gaussian = CondGaussianLayer(Scope([0], [1]), n_nodes=2)
    tc.assertRaises(ValueError, log_likelihood, gaussian, tl.tensor([[0], [1]]))

def test_likelihood_module_cond_f(do_for_all_backends):
    torch.set_default_dtype(torch.float64)

    cond_f = lambda data: {"mean": [0.0, 0.0], "std": [1.0, 1.0]}

    gaussian = CondGaussianLayer(Scope([0], [1]), n_nodes=2, cond_f=cond_f)

    # create test inputs/outputs
    data = tl.tensor([[0.0], [1.0], [-1.0]])
    targets = tl.tensor([[0.398942], [0.241971], [0.241971]])

    probs = likelihood(gaussian, data)
    log_probs = log_likelihood(gaussian, data)

    tc.assertTrue(np.allclose(tl_toNumpy(probs), tl.exp(log_probs)))
    tc.assertTrue(np.allclose(tl_toNumpy(probs), targets))

def test_likelihood_args(do_for_all_backends):
    torch.set_default_dtype(torch.float64)

    gaussian = CondGaussianLayer(Scope([0], [1]), n_nodes=2)

    dispatch_ctx = DispatchContext()
    dispatch_ctx.args[gaussian] = {"mean": [0.0, 0.0], "std": [1.0, 1.0]}

    # create test inputs/outputs
    data = tl.tensor([[0.0], [1.0], [-1.0]])
    targets = tl.tensor([[0.398942], [0.241971], [0.241971]])

    probs = likelihood(gaussian, data, dispatch_ctx=dispatch_ctx)
    log_probs = log_likelihood(gaussian, data, dispatch_ctx=dispatch_ctx)

    tc.assertTrue(np.allclose(tl_toNumpy(probs), tl.exp(log_probs)))
    tc.assertTrue(np.allclose(tl_toNumpy(probs), targets))

def test_likelihood_args_cond_f(do_for_all_backends):
    torch.set_default_dtype(torch.float64)

    gaussian = CondGaussianLayer(Scope([0], [1]), n_nodes=2)

    cond_f = lambda data: {"mean": [0.0, 0.0], "std": [1.0, 1.0]}

    dispatch_ctx = DispatchContext()
    dispatch_ctx.args[gaussian] = {"cond_f": cond_f}

    # create test inputs/outputs
    data = tl.tensor([[0.0], [1.0], [-1.0]])
    targets = tl.tensor([[0.398942], [0.241971], [0.241971]])

    probs = likelihood(gaussian, data, dispatch_ctx=dispatch_ctx)
    log_probs = log_likelihood(gaussian, data, dispatch_ctx=dispatch_ctx)

    tc.assertTrue(np.allclose(tl_toNumpy(probs), tl.exp(log_probs)))
    tc.assertTrue(np.allclose(tl_toNumpy(probs), targets))

def test_layer_likelihood(do_for_all_backends):
    torch.set_default_dtype(torch.float64)

    layer = CondGaussianLayer(
        scope=[Scope([0], [2]), Scope([1], [2]), Scope([0], [2])],
        cond_f=lambda data: {
            "mean": [0.2, 1.0, 2.3],
            "std": [1.0, 0.3, 0.97],
        },
    )

    nodes = [
        CondGaussian(Scope([0], [2]), cond_f=lambda data: {"mean": 0.2, "std": 1.0}),
        CondGaussian(Scope([1], [2]), cond_f=lambda data: {"mean": 1.0, "std": 0.3}),
        CondGaussian(Scope([0], [2]), cond_f=lambda data: {"mean": 2.3, "std": 0.97}),
    ]

    dummy_data = tl.tensor([[0.5, 1.3], [3.9, 0.71], [1.0, 1.0]])

    layer_ll = log_likelihood(layer, dummy_data)
    nodes_ll = tl.concatenate([log_likelihood(node, dummy_data) for node in nodes], axis=1)

    tc.assertTrue(np.allclose(tl_toNumpy(layer_ll), tl_toNumpy(nodes_ll)))

def test_gradient_computation(do_for_all_backends):
    torch.set_default_dtype(torch.float64)

    if do_for_all_backends == "numpy":
        return

    mean = tl.tensor([random.random(), random.random()], requires_grad=True)
    std = tl.tensor(
        [random.random() + 1e-8, random.random() + 1e-8], requires_grad=True
    )  # offset by small number to avoid zero

    torch_gaussian = CondGaussianLayer(
        scope=[Scope([0], [2]), Scope([1], [2])],
        cond_f=lambda data: {"mean": mean, "std": std},
    )

    # create dummy input data (batch size x random variables)
    data = tl.random.random_tensor((3, 2))

    log_probs_torch = log_likelihood(torch_gaussian, data)

    # create dummy targets
    targets_torch = tl.ones((3, 2))

    loss = torch.nn.MSELoss()(log_probs_torch, targets_torch)
    loss.backward()

    tc.assertTrue(mean.grad is not None)
    tc.assertTrue(std.grad is not None)

def test_likelihood_marginalization(do_for_all_backends):
    torch.set_default_dtype(torch.float64)

    gaussian = CondGaussianLayer(
        scope=[Scope([0], [2]), Scope([1], [2])],
        cond_f=lambda data: {
            "mean": random.random(),
            "std": random.random() + 1e-7,
        },
    )
    data = tl.tensor([[float("nan"), float("nan")]])

    # should not raise and error and should return 1
    probs = tl.exp(log_likelihood(gaussian, data))

    tc.assertTrue(np.allclose(tl_toNumpy(probs), tl.tensor([1.0, 1.0])))

def test_support(do_for_all_backends):
    # TODO
    pass

def test_update_backend(do_for_all_backends):
    backends = ["numpy", "pytorch"]
    cond_f = lambda data: {"mean": [0.0, 0.0], "std": [1.0, 1.0]}

    gaussian = CondGaussianLayer(Scope([0], [1]), n_nodes=2, cond_f=cond_f)

    # create test inputs/outputs
    data = tl.tensor([[0.0], [1.0], [-1.0]])

    log_probs = log_likelihood(gaussian, data)

    # make sure that probabilities match python backend probabilities
    for backend in backends:
        with tl.backend_context(backend):
            layer_updated = updateBackend(gaussian)
            log_probs_updated = log_likelihood(layer_updated, tl.tensor(data))
            # check conversion from torch to python
            tc.assertTrue(np.allclose(tl_toNumpy(log_probs), tl_toNumpy(log_probs_updated)))


if __name__ == "__main__":
    torch.set_default_dtype(torch.float64)
    unittest.main()
