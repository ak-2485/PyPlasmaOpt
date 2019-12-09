import numpy as np
import pytest
from pyplasmaopt import CartesianFourierCurve, BiotSavart, StelleratorSymmetricCylindricalFourierCurve

def get_coil(num_quadrature_points=200):
    coil = CartesianFourierCurve(3, np.linspace(0, 1, num_quadrature_points, endpoint=False))
    coil.coefficients[1][0] = 1.
    coil.coefficients[1][1] = 0.5
    coil.coefficients[2][2] = 0.5
    coil.update()
    return coil

@pytest.mark.parametrize("use_cpp", [True, False])
def test_biotsavart_exponential_convergence(use_cpp):
    coil = get_coil()
    points = np.asarray([[-1.41513202e-03,  8.99999382e-01, -3.14473221e-04 ]])
    btrue   = BiotSavart([get_coil(1000)], [1e4]).B(points, use_cpp=use_cpp)
    bcoarse = BiotSavart([get_coil(10)]  , [1e4]).B(points, use_cpp=use_cpp)
    bfine   = BiotSavart([get_coil(20)]  , [1e4]).B(points, use_cpp=use_cpp)
    assert np.linalg.norm(btrue-bfine) < 1e-4 * np.linalg.norm(bcoarse-bfine)

    dbtrue   = BiotSavart([get_coil(1000)], [1e4]).dB_by_dX(points, use_cpp=use_cpp)
    dbcoarse = BiotSavart([get_coil(10)]  , [1e4]).dB_by_dX(points, use_cpp=use_cpp)
    dbfine   = BiotSavart([get_coil(20)]  , [1e4]).dB_by_dX(points, use_cpp=use_cpp)
    assert np.linalg.norm(btrue-bfine) < 1e-4 * np.linalg.norm(bcoarse-bfine)

@pytest.mark.parametrize("use_cpp", [True, False])
def test_biotsavart_dBdX_taylortest(use_cpp):
    coil = get_coil()
    bs = BiotSavart([coil], [1e4])
    points = np.asarray([[-1.41513202e-03,  8.99999382e-01, -3.14473221e-04 ]])
    dB = bs.dB_by_dX(points, use_cpp=use_cpp)
    B0 = bs.B(points, use_cpp=use_cpp)
    for direction in [np.asarray((1., 0, 0)), np.asarray((0, 1., 0)), np.asarray((0, 0, 1.))]:
        deriv = dB[0].dot(direction)
        err = 1e6
        for i in range(5, 10):
            eps = 0.5**i
            Beps = bs.B(points + eps * direction, use_cpp=use_cpp)
            deriv_est = (Beps-B0)/(eps)
            new_err = np.linalg.norm(deriv-deriv_est)
            assert new_err < 0.55 * err
            err = new_err

@pytest.mark.parametrize("use_cpp", [True, False])
def test_biotsavart_gradient_symmetric_and_divergence_free(use_cpp):
    coil = get_coil()
    bs = BiotSavart([coil], [1e4])
    points = np.asarray([[-1.41513202e-03,  8.99999382e-01, -3.14473221e-04 ]])
    dB = bs.dB_by_dX(points, use_cpp=use_cpp)
    assert abs(dB[0][0, 0] + dB[0][1, 1] + dB[0][2, 2]) < 1e-14
    assert np.allclose(dB[0], dB[0].T)

@pytest.mark.parametrize("use_cpp", [True, False])
@pytest.mark.parametrize("by_chainrule", [True, False])
def test_dB_by_dcoilcoeff_taylortest(use_cpp, by_chainrule):
    coil = get_coil()
    bs = BiotSavart([coil], [1e4])
    points = np.asarray([[-1.41513202e-03,  8.99999382e-01, -3.14473221e-04 ]])

    coil_dofs = coil.get_dofs()
    B0 = bs.B(points, use_cpp=use_cpp)[0]

    h = 1e-2 * np.random.rand(len(coil_dofs)).reshape(coil_dofs.shape)
    if by_chainrule:
        dB_dh = h @ bs.dB_by_dcoilcoeff_via_chainrule(points, use_cpp=use_cpp)[0][0,:,:]
    else:
        dB_dh = h @ bs.dB_by_dcoilcoeff(points, use_cpp=use_cpp)[0][0,:,:]
    err = 1e6
    for i in range(5, 10):
        eps = 0.5**i
        coil.set_dofs(coil_dofs + eps * h)
        Bh = bs.B(points, use_cpp=use_cpp)[0]
        deriv_est = (Bh-B0)/eps
        err_new = np.linalg.norm(deriv_est-dB_dh)
        print("err_new %s" % (err_new))
        assert err_new < 0.55 * err
        err = err_new

@pytest.mark.parametrize("use_cpp", [True, False])
@pytest.mark.parametrize("by_chainrule", [True, False])
def test_dB_dX_by_dcoilcoeff_taylortest(use_cpp, by_chainrule):
    if not use_cpp and by_chainrule:
        return
    coil = get_coil()
    bs = BiotSavart([coil], [1e4])
    points = np.asarray([[-1.41513202e-03,  8.99999382e-01, -3.14473221e-04 ]])

    coil_dofs = coil.get_dofs()
    dB_dX0 = bs.dB_by_dX(points, use_cpp=use_cpp)[0]

    h = 1e-2 * np.random.rand(len(coil_dofs)).reshape(coil_dofs.shape)
    if by_chainrule:
        dB_dXdh = np.einsum('i,ijk->jk', h, bs.d2B_by_dXdcoilcoeff_via_chainrule(points, use_cpp=use_cpp)[0][0,:,:,:])
    else:
        dB_dXdh = np.einsum('i,ijk->jk', h, bs.d2B_by_dXdcoilcoeff(points, use_cpp=use_cpp)[0][0,:,:,:])
    err = 1e6
    for i in range(5, 10):
        eps = 0.5**i
        coil.set_dofs(coil_dofs + eps * h)
        dB_dXh = bs.dB_by_dX(points, use_cpp=use_cpp)[0]
        deriv_est = (dB_dXh-dB_dX0)/eps
        err_new = np.linalg.norm(deriv_est-dB_dXdh)
        print("err_new %s" % (err_new))
        assert err_new < 0.55 * err
        err = err_new

def test_d2B_by_dXdX_is_symmetric(use_cpp=False):
    coil = get_coil()
    bs = BiotSavart([coil], [1e4])
    points = np.asarray([[-1.41513202e-03,  8.99999382e-01, -3.14473221e-04 ]])
    d2B_by_dXdX = bs.d2B_by_dXdX(points, use_cpp=use_cpp)
    for i in range(3):
        assert np.allclose(d2B_by_dXdX[0, :, :, i], d2B_by_dXdX[0, :, :, i].T)


@pytest.mark.parametrize("use_cpp", [True, False])
def test_biotsavart_d2B_by_dXdX_taylortest(use_cpp):
    coil = get_coil()
    bs = BiotSavart([coil], [1e4])
    points = np.asarray([[-1.41513202e-03,  8.99999382e-01, -3.14473221e-04 ]])
    dB_by_dX = bs.dB_by_dX(points, use_cpp=use_cpp)
    d2B_by_dXdX = bs.d2B_by_dXdX(points, use_cpp=use_cpp)
    B0 = bs.B(points, use_cpp=use_cpp)
    for direction in [np.asarray((1., 0, 0)), np.asarray((0, 1., 0)), np.asarray((0, 0, 1.))]:
        first_deriv = dB_by_dX[0].dot(direction)
        second_deriv = np.einsum('ijk,i,j->k', d2B_by_dXdX[0], direction, direction)
        err = 1e6
        for i in range(5, 10):
            eps = 0.5**i
            Beps = bs.B(points + eps * direction, use_cpp=use_cpp)
            deriv_est = (Beps-B0)/(eps)
            second_deriv_est = 2*(deriv_est - first_deriv)/eps
            new_err = np.linalg.norm(second_deriv-second_deriv_est)
            assert new_err < 0.55 * err
            err = new_err


if __name__ == "__main__":
    test_dB_by_dcoilcoeff_taylortest(False, True)
    import sys
    sys.exit()
    coil = CartesianFourierCurve(3)
    coil.coefficients[1][0] = 1.
    coil.coefficients[1][1] = 0.5
    coil.coefficients[2][2] = 0.5

    ma = StelleratorSymmetricCylindricalFourierCurve(3, 2)
    ma.coefficients[0][0] = 1.
    ma.coefficients[0][1] = 0.1
    ma.coefficients[1][0] = 0.1

    bs = BiotSavart([coil], [1])
    points = ma.gamma(np.linspace(0., 1., 1000))
    B = bs.B(points)
    dB = bs.dB_by_dX(points)

    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    fig = plt.figure()
    ax = fig.gca(projection='3d')
    coil.plot(plot_derivative=True, show=False, ax=ax)
    p = ax.scatter(points[:, 0], points[:, 1], points[:, 2], c=np.linalg.norm(B, axis=1), cmap=plt.cm.CMRmap)
    # https://stackoverflow.com/questions/15617207/line-colour-of-3d-parametric-curve-in-pythons-matplotlib-pyplot
    fig.colorbar(p)
    plt.show()


