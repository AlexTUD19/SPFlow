import unittest

import numpy as np

from spflow.base.inference import likelihood, log_likelihood
from spflow.base.structure.spn import (
    CondGeometric,
    CondGeometricLayer,
    ProductNode,
    SumNode,
)
from spflow.meta.data import Scope
from spflow.meta.dispatch import DispatchContext


class TestNode(unittest.TestCase):
    def test_likelihood_no_p(self):

        geometric = CondGeometricLayer(Scope([0], [1]), n_nodes=2)
        self.assertRaises(
            ValueError, log_likelihood, geometric, np.array([[0], [1]])
        )

    def test_likelihood_module_cond_f(self):

        cond_f = lambda data: {"p": [0.2, 0.5]}

        geometric = CondGeometricLayer(
            Scope([0], [1]), n_nodes=2, cond_f=cond_f
        )

        # create test inputs/outputs
        data = np.array([[1], [5], [10]])
        targets = np.array(
            [[0.2, 0.5], [0.08192, 0.03125], [0.0268435, 0.000976563]]
        )

        probs = likelihood(geometric, data)
        log_probs = log_likelihood(geometric, data)

        self.assertTrue(np.allclose(probs, np.exp(log_probs)))
        self.assertTrue(np.allclose(probs, targets))

    def test_likelihood_args_p(self):

        geometric = CondGeometricLayer(Scope([0], [1]), n_nodes=2)

        dispatch_ctx = DispatchContext()
        dispatch_ctx.args[geometric] = {"p": [0.2, 0.5]}

        # create test inputs/outputs
        data = np.array([[1], [5], [10]])
        targets = np.array(
            [[0.2, 0.5], [0.08192, 0.03125], [0.0268435, 0.000976563]]
        )

        probs = likelihood(geometric, data, dispatch_ctx=dispatch_ctx)
        log_probs = log_likelihood(geometric, data, dispatch_ctx=dispatch_ctx)

        self.assertTrue(np.allclose(probs, np.exp(log_probs)))
        self.assertTrue(np.allclose(probs, targets))

    def test_likelihood_args_cond_f(self):

        geometric = CondGeometricLayer(Scope([0], [1]), n_nodes=2)

        cond_f = lambda data: {"p": np.array([0.2, 0.5])}

        dispatch_ctx = DispatchContext()
        dispatch_ctx.args[geometric] = {"cond_f": cond_f}

        # create test inputs/outputs
        data = np.array([[1], [5], [10]])
        targets = np.array(
            [[0.2, 0.5], [0.08192, 0.03125], [0.0268435, 0.000976563]]
        )

        probs = likelihood(geometric, data, dispatch_ctx=dispatch_ctx)
        log_probs = log_likelihood(geometric, data, dispatch_ctx=dispatch_ctx)

        self.assertTrue(np.allclose(probs, np.exp(log_probs)))
        self.assertTrue(np.allclose(probs, targets))

    def test_layer_likelihood_1(self):

        geometric_layer = CondGeometricLayer(
            scope=Scope([0], [1]),
            cond_f=lambda data: {"p": [0.2, 0.5]},
            n_nodes=2,
        )
        s1 = SumNode(children=[geometric_layer], weights=[0.3, 0.7])

        geometric_nodes = [
            CondGeometric(Scope([0], [1]), cond_f=lambda data: {"p": 0.2}),
            CondGeometric(Scope([0], [1]), cond_f=lambda data: {"p": 0.5}),
        ]
        s2 = SumNode(children=geometric_nodes, weights=[0.3, 0.7])

        data = np.array([[3], [1], [5]])

        self.assertTrue(
            np.all(log_likelihood(s1, data) == log_likelihood(s2, data))
        )

    def test_layer_likelihood_2(self):

        geometric_layer = CondGeometricLayer(
            scope=[Scope([0], [2]), Scope([1], [2])],
            cond_f=lambda data: {"p": [0.2, 0.5]},
        )
        p1 = ProductNode(children=[geometric_layer])

        geometric_nodes = [
            CondGeometric(Scope([0], [2]), cond_f=lambda data: {"p": 0.2}),
            CondGeometric(Scope([1], [2]), cond_f=lambda data: {"p": 0.5}),
        ]
        p2 = ProductNode(children=geometric_nodes)

        data = np.array([[3, 1], [2, 7], [5, 4]])

        self.assertTrue(
            np.all(log_likelihood(p1, data) == log_likelihood(p2, data))
        )


if __name__ == "__main__":
    unittest.main()
