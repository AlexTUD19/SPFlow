from spflow.torch.structure.layers.leaves.parametric.cond_poisson import CondPoissonLayer, marginalize, toTorch, toBase
from spflow.torch.structure.nodes.leaves.parametric.cond_poisson import CondPoisson
from spflow.base.structure.layers.leaves.parametric.cond_poisson import CondPoissonLayer as BaseCondPoissonLayer
from spflow.meta.contexts.dispatch_context import DispatchContext
from spflow.meta.scope.scope import Scope
import torch
import numpy as np
import unittest


class TestNode(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        torch.set_default_dtype(torch.float64)

    @classmethod
    def teardown_class(cls):
        torch.set_default_dtype(torch.float32)

    def test_layer_initialization(self):
        
        # ----- check attributes after correct initialization -----
        l = CondPoissonLayer(scope=Scope([1]), n_nodes=3)
        # make sure number of creates nodes is correct
        self.assertEqual(len(l.scopes_out), 3)
        # make sure scopes are correct
        self.assertTrue(np.all(l.scopes_out == [Scope([1]), Scope([1]), Scope([1])]))

        # ---- different scopes -----
        l = CondPoissonLayer(scope=Scope([1]), n_nodes=3)
        for layer_scope, node_scope in zip(l.scopes_out, l.scopes_out):
            self.assertEqual(layer_scope, node_scope)

        # ----- invalid number of nodes -----
        self.assertRaises(ValueError, CondPoissonLayer, Scope([0]), n_nodes=0)

        # ----- invalid scope -----
        self.assertRaises(ValueError, CondPoissonLayer, Scope([]), n_nodes=3)
        self.assertRaises(ValueError, CondPoissonLayer, [], n_nodes=3)

        # ----- individual scopes and parameters -----
        scopes = [Scope([1]), Scope([0]), Scope([0])]
        l = CondPoissonLayer(scope=[Scope([1]), Scope([0])], n_nodes=3)
        
        for layer_scope, node_scope in zip(l.scopes_out, scopes):
            self.assertEqual(layer_scope, node_scope)
        
        # -----number of cond_f functions -----
        CondPoissonLayer(Scope([0]), n_nodes=2, cond_f=[lambda data: {'l': 1}, lambda data: {'l': 1}])
        self.assertRaises(ValueError, CondPoissonLayer, Scope([0]), n_nodes=2, cond_f=[lambda data: {'l': 1}])

    def test_retrieve_params(self):

        # ----- float/int parameter values -----
        l_value = 0.73
        l = CondPoissonLayer(scope=Scope([1]), n_nodes=3, cond_f=lambda data: {'l': l_value})

        for l_layer_node in l.retrieve_params(torch.tensor([[1]]), DispatchContext()):
            self.assertTrue(torch.allclose(l_layer_node, torch.tensor(l_value)))

        # ----- list parameter values -----
        l_values = [0.17, 0.8, 0.53]
        l = CondPoissonLayer(scope=Scope([1]), n_nodes=3, cond_f=lambda data: {'l': l_values})

        for l_layer_node, l_value in zip(l.retrieve_params(torch.tensor([[1]]), DispatchContext()), l_values):
            self.assertTrue(torch.allclose(l_layer_node, torch.tensor(l_value)))

        # wrong number of values
        l.set_cond_f(lambda data: {'l': l_values[:-1]})
        self.assertRaises(ValueError, l.retrieve_params, torch.tensor([[1]]), DispatchContext())

        # wrong number of dimensions (nested list)
        l.set_cond_f(lambda data: {'l': [l_values for _ in range(3)]})
        self.assertRaises(ValueError, l.retrieve_params, torch.tensor([[1]]), DispatchContext())

        # ----- numpy parameter values -----
        l.set_cond_f(lambda data: {'l': np.array(l_values)})
        for l_node, l_actual in zip(l.retrieve_params(torch.tensor([[1.0]]), DispatchContext()), l_values):
            self.assertTrue(l_node == l_actual)
        
        # wrong number of values
        l.set_cond_f(lambda data: {'l': np.array(l_values[:-1])})
        self.assertRaises(ValueError, l.retrieve_params, torch.tensor([[1]]), DispatchContext())

        # wrong number of dimensions (nested list)
        l.set_cond_f(lambda data: {'l': np.array([l_values for _ in range(3)])})
        self.assertRaises(ValueError, l.retrieve_params, torch.tensor([[1]]), DispatchContext())

    def test_layer_structural_marginalization(self):

        # ---------- same scopes -----------

        l = CondPoissonLayer(scope=Scope([1]), n_nodes=2)

        # ----- marginalize over entire scope -----
        self.assertTrue(marginalize(l, [1]) == None)

        # ----- marginalize over non-scope rvs -----
        l_marg = marginalize(l, [2])

        self.assertTrue(l_marg.scopes_out == [Scope([1]), Scope([1])])
    
        # ---------- different scopes -----------

        l = CondPoissonLayer(scope=[Scope([1]), Scope([0])])

        # ----- marginalize over entire scope -----
        self.assertTrue(marginalize(l, [0,1]) == None)

        # ----- partially marginalize -----
        l_marg = marginalize(l, [1], prune=True)
        self.assertTrue(isinstance(l_marg, CondPoisson))
        self.assertEqual(l_marg.scope, Scope([0]))

        l_marg = marginalize(l, [1], prune=False)
        self.assertTrue(isinstance(l_marg, CondPoissonLayer))
        self.assertEqual(len(l_marg.scopes_out), 1)

        # ----- marginalize over non-scope rvs -----
        l_marg = marginalize(l, [2])

        self.assertTrue(l_marg.scopes_out == [Scope([1]), Scope([0])])

    def test_layer_dist(self):

        l_values = torch.tensor([0.73, 0.29, 0.5])
        l = CondPoissonLayer(scope=Scope([1]), n_nodes=3)

        # ----- full dist -----
        dist = l.dist(l_values)

        for l_value, l_dist in zip(l_values, dist.rate):
            self.assertTrue(torch.allclose(l_value, l_dist))
        
        # ----- partial dist -----
        dist = l.dist(l_values, [1,2])

        for l_value, l_dist in zip(l_values[1:], dist.rate):
            self.assertTrue(torch.allclose(l_value, l_dist))

        dist = l.dist(l_values, [1,0])

        for l_value, l_dist in zip(reversed(l_values[:-1]), dist.rate):
            self.assertTrue(torch.allclose(l_value, l_dist))

    def test_layer_backend_conversion_1(self):
        
        torch_layer = CondPoissonLayer(scope=[Scope([0]), Scope([1]), Scope([0])])
        base_layer = toBase(torch_layer)

        self.assertTrue(np.all(base_layer.scopes_out == torch_layer.scopes_out))
        self.assertEqual(base_layer.n_out, torch_layer.n_out)
    
    def test_layer_backend_conversion_2(self):

        base_layer = BaseCondPoissonLayer(scope=[Scope([0]), Scope([1]), Scope([0])])
        torch_layer = toTorch(base_layer)

        self.assertTrue(np.all(base_layer.scopes_out == torch_layer.scopes_out))
        self.assertEqual(base_layer.n_out, torch_layer.n_out)


if __name__ == "__main__":
    torch.set_default_dtype(torch.float64)
    unittest.main()