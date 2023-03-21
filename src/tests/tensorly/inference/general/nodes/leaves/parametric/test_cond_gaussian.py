import math
import random
import unittest

import numpy as np
import tensorly as tl
from spflow.tensorly.utils.helper_functions import tl_allclose

from spflow.tensorly.inference import likelihood, log_likelihood
from spflow.tensorly.structure.spn import CondGaussian
from spflow.meta.data import Scope
from spflow.meta.dispatch import DispatchContext


class TestCondGaussian(unittest.TestCase):
    def test_likelihood_no_mean(self):

        gaussian = CondGaussian(Scope([0], [1]), cond_f=lambda data: {"std": 1.0})
        self.assertRaises(KeyError, log_likelihood, gaussian, tl.tensor([[0], [1]]))

    def test_likelihood_no_std(self):

        gaussian = CondGaussian(Scope([0], [1]), cond_f=lambda data: {"mean": 0.0})
        self.assertRaises(KeyError, log_likelihood, gaussian, tl.tensor([[0], [1]]))

    def test_likelihood_no_mean_std(self):

        gaussian = CondGaussian(Scope([0], [1]))
        self.assertRaises(ValueError, log_likelihood, gaussian, tl.tensor([[0], [1]]))

    def test_likelihood_module_cond_f(self):

        cond_f = lambda data: {"mean": 0.0, "std": 1.0}

        gaussian = CondGaussian(Scope([0], [1]), cond_f=cond_f)

        # create test inputs/outputs
        data = tl.tensor([[0.0], [1.0], [1.0]])
        targets = tl.tensor([[0.398942], [0.241971], [0.241971]])

        probs = likelihood(gaussian, data)
        log_probs = log_likelihood(gaussian, data)

        self.assertTrue(tl_allclose(probs, tl.exp(log_probs)))
        self.assertTrue(tl_allclose(probs, targets))

    def test_likelihood_args(self):

        gaussian = CondGaussian(Scope([0], [1]))

        dispatch_ctx = DispatchContext()
        dispatch_ctx.args[gaussian] = {"mean": 0.0, "std": 1.0}

        # create test inputs/outputs
        data = tl.tensor([[0.0], [1.0], [1.0]])
        targets = tl.tensor([[0.398942], [0.241971], [0.241971]])

        probs = likelihood(gaussian, data, dispatch_ctx=dispatch_ctx)
        log_probs = log_likelihood(gaussian, data, dispatch_ctx=dispatch_ctx)

        self.assertTrue(tl_allclose(probs, tl.exp(log_probs)))
        self.assertTrue(tl_allclose(probs, targets))

    def test_likelihood_args_cond_f(self):

        gaussian = CondGaussian(Scope([0], [1]))

        cond_f = lambda data: {"mean": 0.0, "std": 1.0}

        dispatch_ctx = DispatchContext()
        dispatch_ctx.args[gaussian] = {"cond_f": cond_f}

        # create test inputs/outputs
        data = tl.tensor([[0.0], [1.0], [1.0]])
        targets = tl.tensor([[0.398942], [0.241971], [0.241971]])

        probs = likelihood(gaussian, data, dispatch_ctx=dispatch_ctx)
        log_probs = log_likelihood(gaussian, data, dispatch_ctx=dispatch_ctx)

        self.assertTrue(tl_allclose(probs, tl.exp(log_probs)))
        self.assertTrue(tl_allclose(probs, targets))

    def test_likelihood_1(self):

        # ----- unit variance -----
        mean = random.random()
        var = 1.0

        gaussian = CondGaussian(
            Scope([0], [1]),
            cond_f=lambda data: {"mean": mean, "std": math.sqrt(var)},
        )

        # create test inputs/outputs
        data = tl.tensor([[mean], [mean + math.sqrt(var)], [mean - math.sqrt(var)]])
        targets = tl.tensor([[0.398942], [0.241971], [0.241971]])

        probs = likelihood(gaussian, data)
        log_probs = log_likelihood(gaussian, data)

        self.assertTrue(tl_allclose(probs, tl.exp(log_probs)))
        self.assertTrue(tl_allclose(probs, targets))

    def test_likelihood_2(self):

        # ----- larger variance -----
        mean = random.random()
        var = 5.0

        gaussian = CondGaussian(
            Scope([0], [1]),
            cond_f=lambda data: {"mean": mean, "std": math.sqrt(var)},
        )

        # create test inputs/outputs
        data = tl.tensor([[mean], [mean + math.sqrt(var)], [mean - math.sqrt(var)]])
        targets = tl.tensor([[0.178412], [0.108212], [0.108212]])

        probs = likelihood(gaussian, data)
        log_probs = log_likelihood(gaussian, data)

        self.assertTrue(tl_allclose(probs, tl.exp(log_probs)))
        self.assertTrue(tl_allclose(probs, targets))

    def test_likelihood_3(self):

        # ----- smaller variance -----
        mean = random.random()
        var = 0.2

        gaussian = CondGaussian(
            Scope([0], [1]),
            cond_f=lambda data: {"mean": mean, "std": math.sqrt(var)},
        )

        # create test inputs/outputs
        data = tl.tensor([[mean], [mean + math.sqrt(var)], [mean - math.sqrt(var)]])
        targets = tl.tensor([[0.892062], [0.541062], [0.541062]])

        probs = likelihood(gaussian, data)
        log_probs = log_likelihood(gaussian, data)

        self.assertTrue(tl_allclose(probs, tl.exp(log_probs)))
        self.assertTrue(tl_allclose(probs, targets))

    def test_likelihood_mean_none(self):

        # dummy distribution and data
        gaussian = CondGaussian(Scope([0], [1]), cond_f=lambda data: {"mean": None, "std": 1.0})
        data = np.random.randn(1, 3)

        self.assertRaises(Exception, likelihood, gaussian, data)

    def test_likelihood_std_none(self):

        # dummy distribution and data
        gaussian = CondGaussian(Scope([0], [1]), cond_f=lambda data: {"mean": 0.0, "std": None})
        data = np.random.randn(1, 3)

        self.assertRaises(Exception, likelihood, gaussian, data)

    def test_likelihood_marginalization(self):

        gaussian = CondGaussian(Scope([0], [1]), cond_f=lambda data: {"mean": 0.0, "std": 1.0})
        data = tl.tensor([[tl.nan]])

        # should not raise and error and should return 1 (0 in log-space)
        probs = likelihood(gaussian, data)
        log_probs = log_likelihood(gaussian, data)

        self.assertTrue(tl_allclose(probs, tl.exp(log_probs)))
        self.assertTrue(tl_allclose(probs, 1.0))

    def test_support(self):

        # Support for Gaussian distribution: floats (-inf, inf)

        # TODO:
        #   likelihood:     None
        #   log-likelihood: None

        gaussian = CondGaussian(Scope([0], [1]), cond_f=lambda data: {"mean": 0.0, "std": 1.0})

        # check infinite values
        self.assertRaises(ValueError, log_likelihood, gaussian, tl.tensor([[tl.inf]]))
        self.assertRaises(ValueError, log_likelihood, gaussian, tl.tensor([[-tl.inf]]))


if __name__ == "__main__":
    unittest.main()
