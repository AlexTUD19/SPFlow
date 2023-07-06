import unittest

import numpy as np
import torch

from spflow.base.structure.spn import CondBernoulliLayer as BaseCondBernoulliLayer
from spflow.meta.data import FeatureContext, FeatureTypes, Scope
from spflow.meta.dispatch import DispatchContext
from spflow.torch.structure import marginalize, toBase, toTorch
from spflow.torch.structure.spn import CondBernoulli as CondBernoulliTorch
from spflow.torch.structure.spn import CondBernoulliLayer as CondBernoulliLayerTorch

from spflow.tensorly.structure import AutoLeaf
from spflow.tensorly.structure.general.layers.leaves.parametric.general_cond_bernoulli import CondBernoulliLayer


class TestNode(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        torch.set_default_dtype(torch.float64)

    @classmethod
    def teardown_class(cls):
        torch.set_default_dtype(torch.float32)

    def test_layer_initialization(self):

        # ----- check attributes after correct initialization -----
        l = CondBernoulliLayer(scope=Scope([1], [0]), n_nodes=3)
        # make sure number of creates nodes is correct
        self.assertEqual(len(l.scopes_out), 3)
        # make sure scopes are correct
        self.assertTrue(np.all(l.scopes_out == [Scope([1], [0]), Scope([1], [0]), Scope([1], [0])]))

        # ---- different scopes -----
        l = CondBernoulliLayer(scope=Scope([1], [0]), n_nodes=3)
        for layer_scope, node_scope in zip(l.scopes_out, l.scopes_out):
            self.assertEqual(layer_scope, node_scope)

        # ----- invalid number of nodes -----
        self.assertRaises(ValueError, CondBernoulliLayer, Scope([0], [1]), n_nodes=0)

        # ----- invalid scope -----
        self.assertRaises(ValueError, CondBernoulliLayer, Scope([]), n_nodes=3)
        self.assertRaises(ValueError, CondBernoulliLayer, Scope([0]), n_nodes=3)
        self.assertRaises(ValueError, CondBernoulliLayer, [], n_nodes=3)

        # ----- individual scopes and parameters -----
        scopes = [Scope([1], [2]), Scope([0], [2]), Scope([0], [2])]
        l = CondBernoulliLayer(scope=[Scope([1], [2]), Scope([0], [2])], n_nodes=3)

        for layer_scope, node_scope in zip(l.scopes_out, scopes):
            self.assertEqual(layer_scope, node_scope)

        # -----number of cond_f functions -----
        CondBernoulliLayer(
            Scope([0], [1]),
            n_nodes=2,
            cond_f=[lambda data: {"p": 0.5}, lambda data: {"p": 0.5}],
        )
        self.assertRaises(
            ValueError,
            CondBernoulliLayer,
            Scope([0], [1]),
            n_nodes=2,
            cond_f=[lambda data: {"p": 0.5}],
        )

    def test_retrieve_param(self):

        # ----- float/int parameter values -----
        p_value = 0.13
        l = CondBernoulliLayer(scope=Scope([1], [0]), n_nodes=3, cond_f=lambda data: {"p": p_value})

        for p in l.retrieve_params(torch.tensor([[1.0]]), DispatchContext()):
            self.assertTrue(torch.all(p == p_value))

        # ----- list parameter values -----
        p_values = [0.17, 0.8, 0.53]
        l = CondBernoulliLayer(
            scope=Scope([1], [0]),
            n_nodes=3,
            cond_f=lambda data: {"p": p_values},
        )

        for p_layer_node, p_actual in zip(
            l.retrieve_params(torch.tensor([[1.0]]), DispatchContext()),
            p_values,
        ):
            self.assertTrue(torch.all(p_layer_node == p_actual))

        # wrong number of values
        l.set_cond_f(lambda data: {"p": p_values[:-1]})
        self.assertRaises(
            ValueError,
            l.retrieve_params,
            torch.tensor([[1]]),
            DispatchContext(),
        )

        # wrong number of dimensions (nested list)
        l.set_cond_f(lambda data: {"p": [p_values for _ in range(3)]})
        self.assertRaises(
            ValueError,
            l.retrieve_params,
            torch.tensor([[1]]),
            DispatchContext(),
        )

        # ----- numpy parameter values -----
        l.set_cond_f(lambda data: {"p": np.array(p_values)})

        for p_layer_node, p_actual in zip(
            l.retrieve_params(torch.tensor([[1.0]]), DispatchContext()),
            p_values,
        ):
            self.assertTrue(p_layer_node == p_actual)

        # wrong number of values
        l.set_cond_f(lambda data: {"p": np.array(p_values[:-1])})
        self.assertRaises(
            ValueError,
            l.retrieve_params,
            torch.tensor([[1]]),
            DispatchContext(),
        )

        # wrong number of dimensions (nested list)
        l.set_cond_f(lambda data: {"p": np.array([p_values for _ in range(3)])})
        self.assertRaises(
            ValueError,
            l.retrieve_params,
            torch.tensor([[1]]),
            DispatchContext(),
        )

    def test_accept(self):

        # discrete meta type
        self.assertTrue(
            CondBernoulliLayer.accepts(
                [
                    FeatureContext(Scope([0], [2]), [FeatureTypes.Discrete]),
                    FeatureContext(Scope([1], [3]), [FeatureTypes.Discrete]),
                ]
            )
        )

        # Bernoulli feature type class
        self.assertTrue(
            CondBernoulliLayer.accepts(
                [
                    FeatureContext(Scope([0], [2]), [FeatureTypes.Bernoulli]),
                    FeatureContext(Scope([1], [3]), [FeatureTypes.Discrete]),
                ]
            )
        )

        # Bernoulli feature type instance
        self.assertTrue(
            CondBernoulliLayer.accepts(
                [
                    FeatureContext(Scope([0], [2]), [FeatureTypes.Bernoulli(0.5)]),
                    FeatureContext(Scope([1], [3]), [FeatureTypes.Bernoulli(0.5)]),
                ]
            )
        )

        # invalid feature type
        self.assertFalse(
            CondBernoulliLayer.accepts(
                [
                    FeatureContext(Scope([0], [2]), [FeatureTypes.Continuous]),
                    FeatureContext(Scope([1], [3]), [FeatureTypes.Continuous]),
                ]
            )
        )

        # non-conditional scope
        self.assertFalse(CondBernoulliLayer.accepts([FeatureContext(Scope([0]), [FeatureTypes.Discrete])]))

        # multivariate signature
        self.assertFalse(
            CondBernoulliLayer.accepts(
                [
                    FeatureContext(
                        Scope([0, 1], [2]),
                        [FeatureTypes.Discrete, FeatureTypes.Discrete],
                    )
                ]
            )
        )

    def test_initialization_from_signatures(self):

        bernoulli = CondBernoulliLayer.from_signatures(
            [
                FeatureContext(Scope([0], [2]), [FeatureTypes.Discrete]),
                FeatureContext(Scope([1], [3]), [FeatureTypes.Discrete]),
            ]
        )
        self.assertTrue(bernoulli.scopes_out == [Scope([0], [2]), Scope([1], [3])])

        bernoulli = CondBernoulliLayer.from_signatures(
            [
                FeatureContext(Scope([0], [2]), [FeatureTypes.Bernoulli]),
                FeatureContext(Scope([1], [3]), [FeatureTypes.Bernoulli]),
            ]
        )
        self.assertTrue(bernoulli.scopes_out == [Scope([0], [2]), Scope([1], [3])])

        bernoulli = CondBernoulliLayer.from_signatures(
            [
                FeatureContext(Scope([0], [2]), [FeatureTypes.Bernoulli(p=0.75)]),
                FeatureContext(Scope([1], [3]), [FeatureTypes.Bernoulli(p=0.25)]),
            ]
        )
        self.assertTrue(bernoulli.scopes_out == [Scope([0], [2]), Scope([1], [3])])

        # ----- invalid arguments -----

        # invalid feature type
        self.assertRaises(
            ValueError,
            CondBernoulliLayer.from_signatures,
            [FeatureContext(Scope([0], [1]), [FeatureTypes.Continuous])],
        )

        # non-conditional scope
        self.assertRaises(
            ValueError,
            CondBernoulliLayer.from_signatures,
            [FeatureContext(Scope([0]), [FeatureTypes.Discrete])],
        )

        # multivariate signature
        self.assertRaises(
            ValueError,
            CondBernoulliLayer.from_signatures,
            [
                FeatureContext(
                    Scope([0, 1], [2]),
                    [FeatureTypes.Discrete, FeatureTypes.Discrete],
                )
            ],
        )

    def test_autoleaf(self):

        # make sure leaf is registered
        self.assertTrue(AutoLeaf.is_registered(CondBernoulliLayer))

        # make sure leaf is correctly inferred
        self.assertEqual(
            CondBernoulliLayer,
            AutoLeaf.infer(
                [
                    FeatureContext(Scope([0], [2]), [FeatureTypes.Bernoulli()]),
                    FeatureContext(Scope([1], [3]), [FeatureTypes.Bernoulli()]),
                ]
            ),
        )

        # make sure AutoLeaf can return correctly instantiated object
        bernoulli = AutoLeaf(
            [
                FeatureContext(Scope([0], [2]), [FeatureTypes.Bernoulli(p=0.75)]),
                FeatureContext(Scope([1], [3]), [FeatureTypes.Bernoulli(p=0.25)]),
            ]
        )
        self.assertTrue(bernoulli.scopes_out == [Scope([0], [2]), Scope([1], [3])])

    def test_layer_structural_marginalization(self):

        # ---------- same scopes -----------

        l = CondBernoulliLayer(scope=Scope([1], [0]), n_nodes=2)

        # ----- marginalize over entire scope -----
        self.assertTrue(marginalize(l, [1]) == None)

        # ----- marginalize over non-scope rvs -----
        l_marg = marginalize(l, [2])

        self.assertTrue(l_marg.scopes_out == [Scope([1], [0]), Scope([1], [0])])

        # ---------- different scopes -----------

        l = CondBernoulliLayer(scope=[Scope([1], [2]), Scope([0], [2])])

        # ----- marginalize over entire scope -----
        self.assertTrue(marginalize(l, [0, 1]) == None)

        # ----- partially marginalize -----
        l_marg = marginalize(l, [1], prune=True)
        self.assertTrue(isinstance(l_marg, CondBernoulliTorch))
        self.assertEqual(l_marg.scope, Scope([0], [2]))

        l_marg = marginalize(l, [1], prune=False)
        self.assertTrue(isinstance(l_marg, CondBernoulliLayerTorch))
        self.assertEqual(len(l_marg.scopes_out), 1)

        # ----- marginalize over non-scope rvs -----
        l_marg = marginalize(l, [2])

        self.assertTrue(l_marg.scopes_out == [Scope([1], [2]), Scope([0], [2])])

    def test_layer_dist(self):

        p_values = torch.tensor([0.73, 0.29, 0.5])
        l = CondBernoulliLayer(scope=Scope([1], [0]), n_nodes=3)

        # ----- full dist -----
        dist = l.dist(p_values)

        for p_value, p_dist in zip(p_values, dist.probs):
            self.assertTrue(torch.allclose(p_value, p_dist))

        # ----- partial dist -----
        dist = l.dist(p_values, [1, 2])

        for p_value, p_dist in zip(p_values[1:], dist.probs):
            self.assertTrue(torch.allclose(p_value, p_dist))

        dist = l.dist(p_values, [1, 0])

        for p_value, p_dist in zip(reversed(p_values[:-1]), dist.probs):
            self.assertTrue(torch.allclose(p_value, p_dist))

    def test_layer_backend_conversion_1(self):

        torch_layer = CondBernoulliLayer(scope=[Scope([0], [2]), Scope([1], [2]), Scope([0], [2])])
        base_layer = toBase(torch_layer)

        self.assertTrue(np.all(base_layer.scopes_out == torch_layer.scopes_out))
        self.assertEqual(base_layer.n_out, torch_layer.n_out)

    def test_layer_backend_conversion_2(self):

        base_layer = BaseCondBernoulliLayer(scope=[Scope([0], [2]), Scope([1], [2]), Scope([0], [2])])
        torch_layer = toTorch(base_layer)

        self.assertTrue(np.all(base_layer.scopes_out == torch_layer.scopes_out))
        self.assertEqual(base_layer.n_out, torch_layer.n_out)


if __name__ == "__main__":
    torch.set_default_dtype(torch.float64)
    unittest.main()
