import random
import unittest

import torch
import tensorly as tl
import numpy as np

from spflow.meta.data import Scope
from spflow.meta.dispatch import DispatchContext
from spflow.modules.module import log_likelihood, likelihood
from spflow.structure.general.layer.leaf import CondLogNormalLayer
from spflow.structure.general.node.leaf.general_cond_log_normal import CondLogNormal
from spflow.torch.structure.general.layer.leaf.cond_log_normal import updateBackend
from spflow.utils import Tensor
from spflow.tensor import ops as tle

tc = unittest.TestCase()


def test_likelihood_no_mean(do_for_all_backends):
    log_normal = CondLogNormalLayer(
        Scope([0], [1]),
        cond_f=lambda data: {"std": [0.25, 0.25]},
        n_nodes=2,
    )
    tc.assertRaises(KeyError, log_likelihood, log_normal, tl.tensor([[0], [1]]))


def test_likelihood_no_std(do_for_all_backends):
    log_normal = CondLogNormalLayer(Scope([0], [1]), cond_f=lambda data: {"mean": [0.0, 0.0]}, n_nodes=2)
    tc.assertRaises(KeyError, log_likelihood, log_normal, tl.tensor([[0], [1]]))


def test_likelihood_no_mean_std(do_for_all_backends):
    log_normal = CondLogNormalLayer(Scope([0], [1]), n_nodes=2)
    tc.assertRaises(ValueError, log_likelihood, log_normal, tl.tensor([[0], [1]]))


def test_likelihood_module_cond_f(do_for_all_backends):
    cond_f = lambda data: {"mean": [0.0, 0.0], "std": [0.25, 0.25]}

    log_normal = CondLogNormalLayer(Scope([0], [1]), n_nodes=2, cond_f=cond_f)

    # create test inputs/outputs
    data = tl.tensor([[0.5], [1.0], [1.5]])
    targets = tl.tensor([[0.0683495], [1.59577], [0.285554]])

    probs = likelihood(log_normal, data)
    log_probs = log_likelihood(log_normal, data)

    tc.assertTrue(np.allclose(tle.toNumpy(probs), tl.exp(log_probs)))
    tc.assertTrue(np.allclose(tle.toNumpy(probs), targets))


def test_likelihood_args(do_for_all_backends):
    log_normal = CondLogNormalLayer(Scope([0], [1]), n_nodes=2)

    dispatch_ctx = DispatchContext()
    dispatch_ctx.args[log_normal] = {
        "mean": [0.0, 0.0],
        "std": [0.25, 0.25],
    }

    # create test inputs/outputs
    data = tl.tensor([[0.5], [1.0], [1.5]])
    targets = tl.tensor([[0.0683495], [1.59577], [0.285554]])

    probs = likelihood(log_normal, data, dispatch_ctx=dispatch_ctx)
    log_probs = log_likelihood(log_normal, data, dispatch_ctx=dispatch_ctx)

    tc.assertTrue(np.allclose(tle.toNumpy(probs), tl.exp(log_probs)))
    tc.assertTrue(np.allclose(tle.toNumpy(probs), targets))


def test_likelihood_args_cond_f(do_for_all_backends):
    log_normal = CondLogNormalLayer(Scope([0], [1]), n_nodes=2)

    cond_f = lambda data: {"mean": [0.0, 0.0], "std": [0.25, 0.25]}

    dispatch_ctx = DispatchContext()
    dispatch_ctx.args[log_normal] = {"cond_f": cond_f}

    # create test inputs/outputs
    data = tl.tensor([[0.5], [1.0], [1.5]])
    targets = tl.tensor([[0.0683495], [1.59577], [0.285554]])

    probs = likelihood(log_normal, data, dispatch_ctx=dispatch_ctx)
    log_probs = log_likelihood(log_normal, data, dispatch_ctx=dispatch_ctx)

    tc.assertTrue(np.allclose(tle.toNumpy(probs), tl.exp(log_probs)))
    tc.assertTrue(np.allclose(tle.toNumpy(probs), targets))


def test_layer_likelihood(do_for_all_backends):
    layer = CondLogNormalLayer(
        scope=[Scope([0], [2]), Scope([1], [2]), Scope([0], [2])],
        cond_f=lambda data: {
            "mean": [0.2, 1.0, 2.3],
            "std": [1.0, 0.3, 0.97],
        },
    )

    nodes = [
        CondLogNormal(Scope([0], [2]), cond_f=lambda data: {"mean": 0.2, "std": 1.0}),
        CondLogNormal(Scope([1], [2]), cond_f=lambda data: {"mean": 1.0, "std": 0.3}),
        CondLogNormal(Scope([0], [2]), cond_f=lambda data: {"mean": 2.3, "std": 0.97}),
    ]

    dummy_data = tl.tensor([[0.5, 1.3], [3.9, 0.71], [1.0, 1.0]])

    layer_ll = log_likelihood(layer, dummy_data)
    nodes_ll = tl.concatenate([log_likelihood(node, dummy_data) for node in nodes], axis=1)

    tc.assertTrue(np.allclose(tle.toNumpy(layer_ll), tle.toNumpy(nodes_ll)))


def test_gradient_computation(do_for_all_backends):
    if do_for_all_backends == "numpy":
        return

    mean = tl.tensor([random.random(), random.random()], requires_grad=True)
    std = tl.tensor(
        [random.random() + 1e-8, random.random() + 1e-8], requires_grad=True
    )  # offset by small number to avoid zero

    torch_log_normal = CondLogNormalLayer(
        scope=[Scope([0], [2]), Scope([1], [2])],
        cond_f=lambda data: {"mean": mean, "std": std},
    )

    # create dummy input data (batch size x random variables)
    data = tl.random.random_tensor((3, 2))

    log_probs_torch = log_likelihood(torch_log_normal, data)

    # create dummy targets
    targets_torch = tl.ones((3, 2))

    loss = torch.nn.MSELoss()(log_probs_torch, targets_torch)
    loss.backward()

    tc.assertTrue(mean.grad is not None)
    tc.assertTrue(std.grad is not None)


def test_likelihood_marginalization(do_for_all_backends):
    log_normal = CondLogNormalLayer(
        scope=[Scope([0], [2]), Scope([1], [2])],
        cond_f=lambda data: {
            "mean": random.random(),
            "std": random.random() + 1e-7,
        },
    )
    data = tl.tensor([[float("nan"), float("nan")]])

    # should not raise and error and should return 1
    probs = tl.exp(log_likelihood(log_normal, data))

    tc.assertTrue(np.allclose(tle.toNumpy(probs), tl.tensor([1.0, 1.0])))


def test_support(do_for_all_backends):
    # TODO
    pass


def test_update_backend(do_for_all_backends):
    backends = ["numpy", "pytorch"]
    cond_f = lambda data: {"mean": [0.0, 0.0], "std": [0.25, 0.25]}

    log_normal = CondLogNormalLayer(Scope([0], [1]), n_nodes=2, cond_f=cond_f)

    # create test inputs/outputs
    data = tl.tensor([[0.5], [1.0], [1.5]])

    log_probs = log_likelihood(log_normal, data)

    # make sure that probabilities match python backend probabilities
    for backend in backends:
        with tl.backend_context(backend):
            layer_updated = updateBackend(log_normal)
            log_probs_updated = log_likelihood(layer_updated, tl.tensor(data))
            # check conversion from torch to python
            tc.assertTrue(np.allclose(tle.toNumpy(log_probs), tle.toNumpy(log_probs_updated)))


def test_change_dtype(do_for_all_backends):
    cond_f = lambda data: {"mean": [0.0, 0.0], "std": [0.25, 0.25]}

    layer = CondLogNormalLayer(Scope([0], [1]), n_nodes=2, cond_f=cond_f)
    dummy_data = tl.tensor([[0.5], [1.0], [1.5]], dtype=tl.float32)
    layer_ll = log_likelihood(layer, dummy_data)
    tc.assertTrue(layer_ll.dtype == tl.float32)
    layer.to_dtype(tl.float64)
    dummy_data = tl.tensor([[0.5], [1.0], [1.5]], dtype=tl.float64)
    layer_ll_up = log_likelihood(layer, dummy_data)
    tc.assertTrue(layer_ll_up.dtype == tl.float64)


def test_change_device(do_for_all_backends):
    torch.set_default_dtype(torch.float32)
    cuda = torch.device("cuda")
    cond_f = lambda data: {"mean": [0.0, 0.0], "std": [0.25, 0.25]}

    layer = CondLogNormalLayer(Scope([0], [1]), n_nodes=2, cond_f=cond_f)
    dummy_data = tl.tensor([[0.5], [1.0], [1.5]])
    layer_ll = log_likelihood(layer, dummy_data)
    if do_for_all_backends == "numpy":
        tc.assertRaises(ValueError, layer.to_device, cuda)
        return
    tc.assertTrue(layer_ll.device.type == "cpu")
    layer.to_device(cuda)
    dummy_data = tl.tensor([[0.5], [1.0], [1.5]], device=cuda)
    layer_ll = log_likelihood(layer, dummy_data)
    tc.assertTrue(layer_ll.device.type == "cuda")


if __name__ == "__main__":
    torch.set_default_dtype(torch.float32)
    unittest.main()
