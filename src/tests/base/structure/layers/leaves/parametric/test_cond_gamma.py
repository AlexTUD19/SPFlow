from spflow.base.structure.layers.leaves.parametric.cond_gamma import CondGammaLayer, marginalize
from spflow.base.structure.nodes.leaves.parametric.cond_gamma import CondGamma
from spflow.meta.contexts.dispatch_context import DispatchContext
from spflow.meta.scope.scope import Scope
import numpy as np
import unittest


class TestLayer(unittest.TestCase):
    def test_layer_initialization_1(self):

        # ----- check attributes after correct initialization -----

        l = CondGammaLayer(scope=Scope([1]), n_nodes=3)
        # make sure number of creates nodes is correct
        self.assertEqual(len(l.nodes), 3)
        # make sure scopes are correct
        self.assertTrue(np.all(l.scopes_out == [Scope([1]), Scope([1]), Scope([1])]))

        # ---- different scopes -----
        l = CondGammaLayer(scope=Scope([1]), n_nodes=3)
        for node, node_scope in zip(l.nodes, l.scopes_out):
            self.assertEqual(node.scope, node_scope)

        # ----- invalid number of nodes -----
        self.assertRaises(ValueError, CondGammaLayer, Scope([0]), n_nodes=0)

        # ----- invalid scope -----
        self.assertRaises(ValueError, CondGammaLayer, Scope([]), n_nodes=3)
        self.assertRaises(ValueError, CondGammaLayer, [], n_nodes=3)

        # ----- individual scopes and parameters -----
        scopes = [Scope([1]), Scope([0]), Scope([0])]
        l = CondGammaLayer(scope=[Scope([1]), Scope([0])], n_nodes=3)\

        for node, node_scope in zip(l.nodes, scopes):
            self.assertEqual(node.scope, node_scope)
        
        # -----number of cond_f functions -----
        CondGammaLayer(Scope([0]), n_nodes=2, cond_f=[lambda data: {'alpha': 0.5, 'beta': 0.5}, lambda data: {'alpha': 0.5, 'beta': 0.5}])
        self.assertRaises(ValueError, CondGammaLayer, Scope([0]), n_nodes=2, cond_f=[lambda data: {'alpha': 0.5, 'beta': 0.5}])

    def test_retrieve_params(self):

        # ----- float/int parameter values ----- 
        alpha_value = 2
        beta_value = 0.5
        l = CondGammaLayer(scope=Scope([1]), n_nodes=3, cond_f=lambda data: {'alpha': alpha_value, 'beta': beta_value})

        for alpha_node, beta_node in zip(*l.retrieve_params(np.array([[1.0]]), DispatchContext())):
            self.assertTrue(alpha_node == alpha_value)
            self.assertTrue(beta_node == beta_value)

        # ----- list parameter values -----
        alpha_values = [1.0, 5.0, 3.0]
        beta_values = [0.25, 0.5, 0.3]
        l.set_cond_f(lambda data: {'alpha': alpha_values, 'beta': beta_values})

        for alpha_actual, beta_actual, alpha_node, beta_node in zip(alpha_values, beta_values, *l.retrieve_params(np.array([[1.0]]), DispatchContext())):
            self.assertTrue(alpha_actual == alpha_node)
            self.assertTrue(beta_actual == beta_node)

        # wrong number of values
        l.set_cond_f(lambda data: {'alpha': alpha_values[:-1], 'beta': beta_values})
        self.assertRaises(ValueError, l.retrieve_params, np.array([[1]]), DispatchContext())
        l.set_cond_f(lambda data: {'alpha': alpha_values, 'beta': beta_values[:-1]})
        self.assertRaises(ValueError, l.retrieve_params, np.array([[1]]), DispatchContext())

        # wrong number of dimensions (nested list)
        l.set_cond_f(lambda data: {'alpha': [alpha_values for _ in range(3)], 'beta': beta_values})
        self.assertRaises(ValueError, l.retrieve_params, np.array([[1]]), DispatchContext())
        l.set_cond_f(lambda data: {'alpha': alpha_values, 'beta': [beta_values for _ in range(3)]})
        self.assertRaises(ValueError, l.retrieve_params, np.array([[1]]), DispatchContext())

        # ----- numpy parameter values -----
        l.set_cond_f(lambda data: {'alpha': np.array(alpha_values), 'beta': np.array(beta_values)})
        for alpha_actual, beta_actual, alpha_node, beta_node in zip(alpha_values, beta_values, *l.retrieve_params(np.array([[1.0]]), DispatchContext())):
            self.assertTrue(alpha_node == alpha_actual)
            self.assertTrue(beta_node == beta_actual)
    
        # wrong number of values
        l.set_cond_f(lambda data: {'alpha': np.array(alpha_values[:-1]), 'beta': np.array(beta_values)})
        self.assertRaises(ValueError, l.retrieve_params, np.array([[1]]), DispatchContext())
        l.set_cond_f(lambda data: {'alpha': np.array(alpha_values), 'beta': np.array(beta_values[:-1])})
        self.assertRaises(ValueError, l.retrieve_params, np.array([[1]]), DispatchContext())

        # wrong number of dimensions (nested list)
        l.set_cond_f(lambda data: {'alpha': np.array([alpha_values for _ in range(3)]), 'beta': np.array(beta_values)})
        self.assertRaises(ValueError, l.retrieve_params, np.array([[1]]), DispatchContext())
        l.set_cond_f(lambda data: {'alpha': np.array(alpha_values), 'beta': np.array([beta_values for _ in range(3)])})
        self.assertRaises(ValueError, l.retrieve_params, np.array([[1]]), DispatchContext())

    def test_layer_structural_marginalization(self):

        # ---------- same scopes -----------

        l = CondGammaLayer(scope=Scope([1]), n_nodes=2)

        # ----- marginalize over entire scope -----
        self.assertTrue(marginalize(l, [1]) == None)

        # ----- marginalize over non-scope rvs -----
        l_marg = marginalize(l, [2])

        self.assertTrue(l_marg.scopes_out == [Scope([1]), Scope([1])])
    
        # ---------- different scopes -----------

        l = CondGammaLayer(scope=[Scope([1]), Scope([0])])

        # ----- marginalize over entire scope -----
        self.assertTrue(marginalize(l, [0,1]) == None)

        # ----- partially marginalize -----
        l_marg = marginalize(l, [1], prune=True)
        self.assertTrue(isinstance(l_marg, CondGamma))
        self.assertEqual(l_marg.scope, Scope([0]))

        l_marg = marginalize(l, [1], prune=False)
        self.assertTrue(isinstance(l_marg, CondGammaLayer))
        self.assertEqual(len(l_marg.nodes), 1)

        # ----- marginalize over non-scope rvs -----
        l_marg = marginalize(l, [2])

        self.assertTrue(l_marg.scopes_out == [Scope([1]), Scope([0])])


if __name__ == "__main__":
    unittest.main()