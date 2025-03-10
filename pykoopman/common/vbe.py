"""module for 1D viscous burgers"""
from __future__ import annotations

import numpy as np
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from scipy.fft import fft
from scipy.fft import fftfreq
from scipy.fft import ifft

from pykoopman.common.examples import rk4


class vbe:
    """
    1D viscous Burgers equation

    u_t = -u*u_x + \nu u_{xx}

    periodic B.C. PDE is solved using spectral methods
    """

    def __init__(self, n, x, dt, nu=0.1, L=2 * np.pi):
        self.n_states = n
        self.x = x
        self.nu = nu
        dk = 2 * np.pi / L
        self.k = fftfreq(self.n_states, 1.0 / self.n_states) * dk
        self.dt = dt

    def sys(self, t, x, u):
        xk = fft(x)

        # 3/2 truncation rule
        xk[self.n_states // 3 : 2 * self.n_states // 3] = 0j
        x = ifft(xk)

        # nonlinear advection
        tmp_nl_k = fft(-0.5 * x * x)
        tmp_nl_x_k = 1j * self.k * tmp_nl_k

        # linear viscous term
        tmp_vis_k = -self.nu * self.k**2 * xk

        # return back to physical space
        y = np.real(ifft(tmp_nl_x_k + tmp_vis_k))
        return y

    def simulate(self, x0, n_int, n_sample):
        # n_traj = x0.shape[1]
        x = x0
        u = np.zeros((n_int, 1))
        X = np.zeros((n_int // n_sample, self.n_states))
        t = 0
        j = 0
        t_list = []
        for step in range(n_int):
            t += self.dt
            y = rk4(0, x, u[step, :], self.dt, self.sys)
            if (step + 1) % n_sample == 0:
                X[j, :] = y
                j += 1
                t_list.append(t)
            x = y
        return X, np.array(t_list)

    def collect_data_continuous(self, x0):
        """
        collect training data pairs - continuous sense.

        given x0, with shape (n_dim, n_traj), the function
        returns dx/dt with shape (n_dim, n_traj)
        """

        n_traj = x0.shape[0]
        u = np.zeros((n_traj, 1))
        X = x0
        Y = []
        for i in range(n_traj):
            y = self.sys(0, x0[i], u[i])
            Y.append(y)
        Y = np.vstack(Y)
        return X, Y

    def collect_one_step_data_discrete(self, x0):
        """
        collect training data pairs - discrete sense.

        given x0, with shape (n_dim, n_traj), the function
        returns system state x1 after self.dt with shape
        (n_dim, n_traj)
        """

        n_traj = x0.shape[0]
        X = x0
        Y = []
        for i in range(n_traj):
            y, _ = self.simulate(x0[i], n_int=1, n_sample=1)
            Y.append(y)
        Y = np.vstack(Y)
        return X, Y

    def collect_one_trajectory_data(self, x0, n_int, n_sample):
        x = x0
        y, _ = self.simulate(x, n_int, n_sample)
        return y

    def visualize_data(self, x, t, X):
        plt.figure(figsize=(6, 6))
        ax = plt.axes(projection=Axes3D.name)
        for i in range(X.shape[0]):
            ax.plot(x, X[i], zs=t[i], zdir="t", label="time = " + str(i * self.dt))
        # plt.legend(loc='best')
        ax.view_init(elev=35.0, azim=-65, vertical_axis="y")
        ax.set(ylabel=r"$u(x,t)$", xlabel=r"$x$", zlabel=r"time $t$")
        plt.title("1D Viscous Burgers equation (Kutz et al., Complexity, 2018)")
        plt.show()

    def visualize_state_space(self, X):
        u, s, vt = np.linalg.svd(X, full_matrices=False)
        plt.figure(figsize=(6, 6))
        plt.semilogy(s)
        plt.xlabel("number of SVD terms")
        plt.ylabel("singular values")
        plt.title("PCA singular value decays")
        plt.show()

        # this is a pde problem so the number of snapshots are smaller than dof
        pca_1, pca_2, pca_3 = u[:, 0], u[:, 1], u[:, 2]
        plt.figure(figsize=(6, 6))
        ax = plt.axes(projection=Axes3D.name)
        ax.plot3D(pca_1, pca_2, pca_3, "k-o")
        ax.set(xlabel="pc1", ylabel="pc2", zlabel="pc3")
        plt.title("PCA visualization")
        plt.show()


if __name__ == "__main__":
    n = 256
    x = np.linspace(-15, 15, n, endpoint=False)
    u0 = np.exp(-((x + 2) ** 2))
    # u0 = 2.0 / np.cosh(x)
    # u0 = u0.reshape(-1,1)
    n_int = 3000
    n_snapshot = 30
    dt = 30.0 / n_int
    n_sample = n_int // n_snapshot

    model = vbe(n, x, dt=dt, L=30)
    X, t = model.simulate(u0, n_int, n_sample)

    print(X.shape)
    # print(X[:,-1].max())

    # usage: visualize the data in physical space
    model.visualize_data(x, t, X)
    print(t)

    # usage: visualize the data in state space
    model.visualize_state_space(X)

    # usage: collect continuous data pair: x and dx/dt
    x0_array = np.vstack([u0, u0, u0])
    X, Y = model.collect_data_continuous(x0_array)

    print(X.shape)
    print(Y.shape)

    # usage: collect discrete data pair
    x0_array = np.vstack([u0, u0, u0])
    X, Y = model.collect_one_step_data_discrete(x0_array)

    print(X.shape)
    print(Y.shape)

    # usage: collect one trajectory data
    X = model.collect_one_trajectory_data(u0, n_int, n_sample)
    print(X.shape)
