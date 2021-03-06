# -*- coding: utf-8 -*-
"""
Created on Wed Nov 26 11:25:00 2014

@author: Carsten Knoll
"""

import unittest
import sympy as sp
from sympy import sin, cos, Matrix
import symbtools as st
import symbtools.modeltools as mt
import sys


from IPython import embed as IPS


class ModelToolsTest(unittest.TestCase):

    def setUp(self):
        pass

    def test_simple1(self):
        q1, = qq  = sp.Matrix(sp.symbols('q1,'))
        F1, = FF  = sp.Matrix(sp.symbols('F1,'))

        m = sp.Symbol('m')

        q1d = st.time_deriv(q1, qq)
        q1dd = st.time_deriv(q1, qq, order=2)

        T = q1d**2*m/2
        V = 0

        mod = mt.generate_symbolic_model(T, V, qq, FF)

        eq = m*q1dd - F1

        self.assertEqual(mod.eqns[0], eq)

        # test the application of the @property
        M = mod.MM
        self.assertEqual(M[0], m)

    def test_cart_pole(self):
        p1, q1 = ttheta = sp.Matrix(sp.symbols('p1, q1'))
        F1, = FF = sp.Matrix(sp.symbols('F1,'))

        params = sp.symbols('m0, m1, l1, g')
        m0, m1, l1, g = params

        pdot1 = st.time_deriv(p1, ttheta)
        # q1dd = st.time_deriv(q1, ttheta, order=2)

        ex = Matrix([1,0])
        ey = Matrix([0,1])

        S0 = ex*q1  # joint of the pendulum
        S1 = S0 - mt.Rz(p1)*ey*l1  # center of mass

        #velocity
        S0d = st.time_deriv(S0, ttheta)
        S1d = st.time_deriv(S1, ttheta)

        T_rot = 0  # no moment of inertia (mathematical pendulum)
        T_trans = ( m0*S0d.T*S0d + m1*S1d.T*S1d )/2
        T = T_rot + T_trans[0]

        V = m1*g*S1[1]
        
        with self.assertRaises(ValueError) as cm:
            # wrong length of external forces
            mt.generate_symbolic_model(T, V, ttheta, [F1])
            
        with self.assertRaises(ValueError) as cm:
            # wrong length of external forces
            mt.generate_symbolic_model(T, V, ttheta, [F1, 0, 0])
            

        QQ = sp.Matrix([0, F1])
        mod = mt.generate_symbolic_model(T, V, ttheta, [0, F1])
        mod_1 = mt.generate_symbolic_model(T, V, ttheta, QQ)
        mod_2 = mt.generate_symbolic_model(T, V, ttheta, QQ.T)
        
        self.assertEqual(mod.eqns, mod_1.eqns)
        self.assertEqual(mod.eqns, mod_2.eqns)
        
        mod.eqns.simplify()

        M = mod.MM
        M.simplify()

        M_ref = Matrix([[l1**2*m1, l1*m1*cos(p1)], [l1*m1*cos(p1), m1 + m0]])
        self.assertEqual(M, M_ref)

        rest = mod.eqns.subs(st.zip0((mod.ttdd)))
        rest_ref = Matrix([[g*l1*m1*sin(p1)], [-F1 - l1*m1*pdot1**2*sin(p1)]])

        self.assertEqual(M, M_ref)

        mod.calc_state_eq(simplify=True)
        mod.calc_coll_part_lin_state_eq(simplify=True)

        pdot1, qdot1 = mod.ttd

        ff_ref = sp.Matrix([[pdot1],[qdot1], [-g*sin(p1)/l1], [0]])
        gg_ref = sp.Matrix([[0], [0], [-cos(p1)/l1], [1]])

        self.assertEqual(mod.ff, ff_ref)
        self.assertEqual(mod.gg, gg_ref)

    def test_simple_pendulum_with_actuated_mountpoint(self):

        np = 1
        nq = 2
        n = np + nq
        pp = st.symb_vector("p1:{0}".format(np+1))
        qq = st.symb_vector("q1:{0}".format(nq+1))

        p1, q1, q2 = ttheta = st.row_stack(pp, qq)
        pdot1, qdot1, qdot2 = tthetad = st.time_deriv(ttheta, ttheta)
        mud = st.time_deriv(ttheta, ttheta, order=2)
        params = sp.symbols('l3, l4, s3, s4, J3, J4, m1, m2, m3, m4, g')
        l3, l4, s3, s4, J3, J4, m1, m2, m3, m4, g = params

        tau1, tau2 = ttau= st.symb_vector("tau1, tau2")

        ## Geometry

        ex = sp.Matrix([1,0])
        ey = sp.Matrix([0,1])

        # Koordinaten der Schwerpunkte und Gelenke
        S1 = ex*q1
        S2 = ex*q1 + ey*q2
        G3 = S2 # Gelenk

        # Schwerpunkt des Pendels #zeigt nach oben
        S3 = G3 + mt.Rz(p1)*ey*s3

        # Zeitableitungen der Schwerpunktskoordinaten
        Sd1, Sd2, Sd3 = st.col_split(st.time_deriv(st.col_stack(S1, S2, S3), ttheta)) ##

        # Energy
        T_rot = ( J3*pdot1**2 )/2
        T_trans = ( m1*Sd1.T*Sd1  +  m2*Sd2.T*Sd2 + m3*Sd3.T*Sd3 )/2
        T = T_rot + T_trans[0]
        V = m1*g*S1[1] + m2*g*S2[1] + m3*g*S3[1]

        external_forces = [0, tau1, tau2]
        assert not any(external_forces[:np])
        mod = mt.generate_symbolic_model(T, V, ttheta, external_forces)
        mod.calc_coll_part_lin_state_eq(simplify=True)

        #pdot1, qdot1, qdot2 = mod.ttd

        ff_ref = sp.Matrix([[pdot1], [qdot1], [qdot2], [g*m3*s3*sin(p1)/(J3 + m3*s3**2)], [0], [0]])
        gg_ref_part = sp.Matrix([m3*s3*cos(p1)/(J3 + m3*s3**2), m3*s3*sin(p1)/(J3 + m3*s3**2)]).T

        self.assertEqual(mod.ff, ff_ref)
        self.assertEqual(mod.gg[-3, :], gg_ref_part)

    def test_two_link_manipulator(self):
        p1, q1 = ttheta = sp.Matrix(sp.symbols('p1, q1'))
        pdot1, qdot1 = st.time_deriv(ttheta, ttheta)
        tau1, = ttau = sp.Matrix(sp.symbols('F1,'))

        params = sp.symbols('m1, m2, l1, l2, s1, s2, J1, J2')
        m1, m2, l1, l2, s1, s2, J1, J2 = params

        ex = Matrix([1,0])
        ey = Matrix([0,1])

        S1 = mt.Rz(q1)*ex*s1  # center of mass (first link)
        G1 = mt.Rz(q1)*ex*l1  # first joint
        S2 = G1 + mt.Rz(q1+p1)*ex*s2

        #velocity
        S1d = st.time_deriv(S1, ttheta)
        S2d = st.time_deriv(S2, ttheta)

        T_rot = (J1*qdot1**2 + J2*(qdot1 + pdot1)**2) / 2

        T_trans = ( m1*S1d.T*S1d + m2*S2d.T*S2d )/2
        T = T_rot + T_trans[0]

        V = 0

        mod = mt.generate_symbolic_model(T, V, ttheta, [tau1, 0])
        #mod.eqns.simplify()

        #mod.calc_coll_part_lin_state_eq(simplify=True)
        mod.calc_lbi_nf_state_eq(simplify=True)

        w1 = mod.ww[0]

        kappa = l1*m2*s2 / (J2 + m2*s2**2)
        fz4 = - kappa * qdot1*sin(p1) *(w1 - kappa*qdot1*cos(p1))
        fzref = sp.Matrix([[                               qdot1],
                           [                                   0],
                           [ (-qdot1*(1 + kappa*cos(p1) ) ) + w1],
                           [                                 fz4]])

        w_def_ref = pdot1 + qdot1*(1+kappa*cos(p1))
        self.assertEqual(mod.gz, sp.Matrix([0, 1, 0, 0]))

        fz_diff = mod.fz - fzref
        fz_diff.simplify()
        self.assertEqual(fz_diff, sp.Matrix([0, 0, 0, 0]))

        diff = mod.ww_def[0,0] - w_def_ref
        self.assertEqual(diff.simplify(), 0)

    def test_unicycle(self):
        # test the generation of Lagrange-Byrnes-Isidori-Normal form

        theta = st.symb_vector("p1, q1, q2")
        p1, q1, q2 = theta
        theta

        params = sp.symbols('l1, l2, s1, s2, delta0, delta1, delta2, J0, J1, J2, m0, m1, m2, r, g')
        l1, l2, s1, s2, delta0, delta1, delta2, J0, J1, J2, m0, m1, m2, r, g = params

        QQ = sp.symbols("Q0, Q1, Q2")
        Q0, Q1, Q2 = QQ

        mu = st.time_deriv(theta, theta)
        p1d, q1d, q2d = mu

        # Geometry
        ex = Matrix([1,0])
        ey = Matrix([0,1])

        M0 = Matrix([-r*p1, r])

        S1 = M0 + mt.Rz(p1+q1)*ey*s1
        S2 = M0 + mt.Rz(p1+q1)*ey*l1+mt.Rz(p1+q1+q2)*ey*s2

        M0d = st.time_deriv(M0, theta)
        S1d = st.time_deriv(S1, theta)
        S2d = st.time_deriv(S2, theta)

        # Energy
        T_rot = ( J0*p1d**2 + J1*(p1d+q1d)**2 + J2*(p1d+ q1d+q2d)**2 )/2
        T_trans = ( m0*M0d.T*M0d  +  m1*S1d.T*S1d  +  m2*S2d.T*S2d )/2

        T = T_rot + T_trans[0]

        V = m1*g*S1[1] + m2*g*S2[1]

        mod = mt.generate_symbolic_model(T, V, theta, [0, Q1, Q2])
        mod.calc_lbi_nf_state_eq()

    def test_triple_pendulum(self):

        np = 1
        nq = 2
        pp = sp.Matrix( sp.symbols("p1:{0}".format(np+1) ) )
        qq = sp.Matrix( sp.symbols("q1:{0}".format(nq+1) ) )
        ttheta = st.row_stack(pp, qq)
        Q1, Q2 = sp.symbols('Q1, Q2')


        p1_d, q1_d, q2_d = mu = st.time_deriv(ttheta, ttheta)
        p1_dd, q1_dd, q2_dd = mu_d = st.time_deriv(ttheta, ttheta, order=2)

        p1, q1, q2 = ttheta

        # reordering according to chain
        kk = sp.Matrix([q1, q2, p1])
        kd1, kd2, kd3 = q1_d, q2_d, p1_d


        params = sp.symbols('l1, l2, l3, l4, s1, s2, s3, s4, J1, J2, J3, J4, m1, m2, m3, m4, g')
        l1, l2, l3, l4, s1, s2, s3, s4, J1, J2, J3, J4, m1, m2, m3, m4, g = params


        # geometry

        mey = -Matrix([0,1])

        # coordinates for centers of inertia and joints

        S1 = mt.Rz(kk[0])*mey*s1
        G1 = mt.Rz(kk[0])*mey*l1

        S2 = G1 + mt.Rz(sum(kk[:2]))*mey*s2
        G2 = G1 + mt.Rz(sum(kk[:2]))*mey*l2

        S3 = G2 + mt.Rz(sum(kk[:3]))*mey*s3
        G3 = G2 + mt.Rz(sum(kk[:3]))*mey*l3

        # velocities of joints and center of inertia
        Sd1 = st.time_deriv(S1, ttheta)
        Sd2 = st.time_deriv(S2, ttheta)
        Sd3 = st.time_deriv(S3, ttheta)

        # energy
        T_rot = ( J1*kd1**2 + J2*(kd1 + kd2)**2 + J3*(kd1 + kd2 + kd3)**2)/2
        T_trans = ( m1*Sd1.T*Sd1 + m2*Sd2.T*Sd2 + m3*Sd3.T*Sd3)/2

        T = T_rot + T_trans[0]
        V = m1*g*S1[1] + m2*g*S2[1] + m3*g*S3[1]

        external_forces = [0, Q1, Q2]
        mod = mt.generate_symbolic_model(T, V, ttheta, external_forces, simplify=False)

        eqns_ref = Matrix([[J3*(2*p1_dd + 2*q1_dd + 2*q2_dd)/2 + g*m3*s3*sin(p1 + q1 + q2) + m3*s3*(-l1*q1_d**2*sin(q1) + l1*q1_dd*cos(q1) - l2*(q1_d + q2_d)**2*sin(q1 + q2) + l2*(q1_dd + q2_dd)*cos(q1 + q2) - s3*(p1_d + q1_d + q2_d)**2*sin(p1 + q1 + q2) + s3*(p1_dd + q1_dd + q2_dd)*cos(p1 + q1 + q2))*cos(p1 + q1 + q2) + m3*s3*(l1*q1_d**2*cos(q1) + l1*q1_dd*sin(q1) + l2*(q1_d + q2_d)**2*cos(q1 + q2) + l2*(q1_dd + q2_dd)*sin(q1 + q2) + s3*(p1_d + q1_d + q2_d)**2*cos(p1 + q1 + q2) + s3*(p1_dd + q1_dd + q2_dd)*sin(p1 + q1 + q2))*sin(p1 + q1 + q2)], [J1*q1_dd + J2*(2*q1_dd + 2*q2_dd)/2 + J3*(2*p1_dd + 2*q1_dd + 2*q2_dd)/2 - Q1 + g*m1*s1*sin(q1) + \
        g*m2*(l1*sin(q1) + s2*sin(q1 + q2)) + g*m3*(l1*sin(q1) + l2*sin(q1 + q2) + s3*sin(p1 + q1 + q2)) + m1*q1_dd*s1**2*sin(q1)**2 + m1*q1_dd*s1**2*cos(q1)**2 + m2*(2*l1*sin(q1) + 2*s2*sin(q1 + q2))*(l1*q1_d**2*cos(q1) + l1*q1_dd*sin(q1) + s2*(q1_d + q2_d)**2*cos(q1 + q2) + s2*(q1_dd + q2_dd)*sin(q1 + q2))/2 + m2*(2*l1*cos(q1) + 2*s2*cos(q1 + q2))*(-l1*q1_d**2*sin(q1) + l1*q1_dd*cos(q1) - s2*(q1_d + q2_d)**2*sin(q1 + q2) + s2*(q1_dd + q2_dd)*cos(q1 + q2))/2 + m3*(2*l1*sin(q1) + 2*l2*sin(q1 + q2) + 2*s3*sin(p1 + q1 + q2))*(l1*q1_d**2*cos(q1) + l1*q1_dd*sin(q1) + l2*(q1_d + q2_d)**2*cos(q1 + q2) + l2*(q1_dd + q2_dd)*sin(q1 + q2) + s3*(p1_d + q1_d + q2_d)**2*cos(p1 + q1 + q2) + s3*(p1_dd + q1_dd + q2_dd)*sin(p1 + q1 + q2))/2 + m3*(2*l1*cos(q1) + 2*l2*cos(q1 + q2) + 2*s3*cos(p1 + q1 + q2))*(-l1*q1_d**2*sin(q1) + l1*q1_dd*cos(q1) - l2*(q1_d + q2_d)**2*sin(q1 + q2) + l2*(q1_dd + q2_dd)*cos(q1 + q2) - \
        s3*(p1_d + q1_d + q2_d)**2*sin(p1 + q1 + q2) + s3*(p1_dd + q1_dd + q2_dd)*cos(p1 + q1 + q2))/2], [J2*(2*q1_dd + 2*q2_dd)/2 + J3*(2*p1_dd + 2*q1_dd + 2*q2_dd)/2 - Q2 + g*m2*s2*sin(q1 + q2) + g*m3*(l2*sin(q1 + q2) + s3*sin(p1 + q1 + q2)) + m2*s2*(-l1*q1_d**2*sin(q1) + l1*q1_dd*cos(q1) - s2*(q1_d + q2_d)**2*sin(q1 + q2) + s2*(q1_dd + q2_dd)*cos(q1 + q2))*cos(q1 + q2) + \
        m2*s2*(l1*q1_d**2*cos(q1) + l1*q1_dd*sin(q1) + s2*(q1_d + q2_d)**2*cos(q1 + q2) + s2*(q1_dd + q2_dd)*sin(q1 + q2))*sin(q1 + q2) + m3*(2*l2*sin(q1 + q2) + 2*s3*sin(p1 + q1 + q2))*(l1*q1_d**2*cos(q1) + l1*q1_dd*sin(q1) + l2*(q1_d + q2_d)**2*cos(q1 + q2) + l2*(q1_dd + q2_dd)*sin(q1 + q2) + s3*(p1_d + q1_d + q2_d)**2*cos(p1 + q1 + q2) + s3*(p1_dd + q1_dd + q2_dd)*sin(p1 + q1 + q2))/2 + m3*(2*l2*cos(q1 + q2) + 2*s3*cos(p1 + q1 + q2))*(-l1*q1_d**2*sin(q1) + l1*q1_dd*cos(q1) - l2*(q1_d + q2_d)**2*sin(q1 + q2) + l2*(q1_dd + q2_dd)*cos(q1 + q2) - s3*(p1_d + q1_d + q2_d)**2*sin(p1 + q1 + q2) + s3*(p1_dd + q1_dd + q2_dd)*cos(p1 + q1 + q2))/2]])

        self.assertEqual(eqns_ref, mod.eqns)


class ModelToolsTest2(unittest.TestCase):

    def setUp(self):
        pass

    def test_transform_2nd_to_1st(self):

        def intern_test(np, nq):
            N = np + nq
            xx = st.symb_vector('x1:{0}'.format(N*2+1))

            P0 = st.symbMatrix(np, N, s='A')
            P1 = st.symbMatrix(np, N, s='B')
            P2 = st.symbMatrix(np, N, s='C')

            P0bar, P1bar = mt.transform_2nd_to_1st_order_matrices(P0, P1, P2, xx)

            self.assertEqual(P0bar[:N, N:], sp.eye(N))
            self.assertEqual(P1bar[:N, :N], -sp.eye(N))

            self.assertEqual(P0bar[N:, :N], P0)
            self.assertEqual(P1bar[N:, :], P1.row_join(P2))

        intern_test(1, 3)
        intern_test(2, 2)
        intern_test(3, 1)


def main():
    # remove command line args which should not be passed to the testframework
    if 'all' in sys.argv:
        sys.argv.remove('all')
    
    unittest.main()


if __name__ == '__main__':
    main()
