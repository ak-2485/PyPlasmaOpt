import numpy as np
import pytest
from pyplasmaopt import CartesianFourierCurve, BiotSavart, StelleratorSymmetricCylindricalFourierCurve, SquaredMagneticFieldNormOnCurve, SquaredMagneticFieldGradientNormOnCurve

def get_coil():
    coil = CartesianFourierCurve(3, np.linspace(0, 1, 20, endpoint=False))
    coil.coefficients[1][0] = 1.
    coil.coefficients[1][1] = 0.5
    coil.coefficients[2][2] = 0.5
    return coil

def get_magnetic_axis():
    ma = StelleratorSymmetricCylindricalFourierCurve(3, 2, np.linspace(0, 1, 20, endpoint=False))
    ma.coefficients[0][0] = 1.
    ma.coefficients[0][1] = 0.1
    ma.coefficients[1][0] = 0.1
    return ma

@pytest.mark.parametrize("gradient", [True, False])
def test_magnetic_field_objective_by_dcoilcoeffs(gradient):
    coils = [get_coil()]
    currents = [1e4]
    ma = get_magnetic_axis()
    bs = BiotSavart(coils, currents)
    if gradient:
        J = SquaredMagneticFieldGradientNormOnCurve(ma, bs)
    else:
        J = SquaredMagneticFieldNormOnCurve(ma, bs)
    J0 = J.J()
    coil_dofs = coils[0].get_dofs()
    h = 1e-2 * np.random.rand(len(coil_dofs)).reshape(coil_dofs.shape)
    dJ = J.dJ_by_dcoilcoefficients()
    deriv = np.sum(dJ[0] * h)
    err = 1e6
    for i in range(5, 10):
        eps = 0.5**i
        coils[0].set_dofs(coil_dofs + eps * h)
        Jh = J.J()
        deriv_est = (Jh-J0)/eps
        err_new = np.linalg.norm(deriv_est-deriv)
        print("err_new %s" % (err_new))
        assert err_new < 0.55 * err
        err = err_new

@pytest.mark.parametrize("gradient", [True, False])
def test_magnetic_field_objective_by_dcurvecoeffs(gradient):
    coils = [get_coil()]
    currents = [1e4]
    ma = get_magnetic_axis()
    bs = BiotSavart(coils, currents)
    if gradient:
        J = SquaredMagneticFieldGradientNormOnCurve(ma, bs)
    else:
        J = SquaredMagneticFieldNormOnCurve(ma, bs)
    J0 = J.J()
    curve_dofs = ma.get_dofs()
    h = 1e-1 * np.random.rand(len(curve_dofs)).reshape(curve_dofs.shape)
    dJ = J.dJ_by_dcurvecoefficients()
    deriv = np.sum(dJ * h)
    err = 1e6
    for i in range(5, 10):
        eps = 0.5**i
        ma.set_dofs(curve_dofs + eps * h)
        Jh = J.J()
        deriv_est = (Jh-J0)/eps
        err_new = np.linalg.norm(deriv_est-deriv)
        print("err_new %s" % (err_new))
        assert err_new < 0.55 * err
        err = err_new

if __name__ == "__main__":
    test_magnetic_field_objective_by_dcoilcoeffs()
    test_magnetic_field_objective_by_dcurvecoeffs()