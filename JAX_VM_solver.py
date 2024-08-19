# -*- coding: utf-8 -*-
"""
Created on Sun Jun 23 10:55:45 2024

@author: cristian
"""

import jax
import jax.numpy as jnp
from jax.scipy.signal import convolve
from jax.numpy.fft import fftn, ifftn, fftshift, ifftshift
from jax.scipy.special import factorial
from jax.scipy.integrate import trapezoid
from jax.experimental.ode import odeint
from quadax import quadgk
from functools import partial
import json
import matplotlib.pyplot as plt

#######################################################################################################################
# Perhaps move examples to separate file.
def Orszag_Tang(Lx, Ly, Omega_ce, mi_me):
    """
    I have to add docstrings!
    """
    
    vte = jnp.sqrt(0.25 / 2) * Omega_ce # Electron thermal velocity.
    vti = vte * jnp.sqrt(1 / mi_me) # Ion thermal velocity.
    deltaB = 0.2 # In-plane magnetic field amplitude. 
    U0 = deltaB * Omega_ce / jnp.sqrt(mi_me) # Fluid velocity amplitude.
    
    # Wavenumbers.
    kx = 2 * jnp.pi / Lx
    ky = 2 * jnp.pi / Ly
    
    # Electron and ion fluid velocities.
    Ue = lambda x, y, z: U0 * jnp.array([-jnp.sin(ky * y), jnp.sin(kx * x), -deltaB * Omega_ce * (2 * kx * jnp.cos(2 * kx * x) + ky * jnp.cos(ky * y))])
    Ui = lambda x, y, z: U0 * jnp.array([-jnp.sin(ky * y), jnp.sin(kx * x), jnp.zeros_like(x)])
    
    # Magnetic and electric fields.
    B = lambda x, y, z: jnp.array([-deltaB * jnp.sin(ky * y), deltaB * jnp.sin(2 * kx * x), jnp.ones_like(x)])
    E = lambda x, y, z: jnp.array([jnp.zeros_like(x), jnp.zeros_like(x), jnp.zeros_like(x)]) # Is this consistent with fe, fi?
    
    # Electron and ion distribution functions.
    fe = (lambda x, y, z, vx, vy, vz: (1 / (((2 * jnp.pi) ** (3 / 2)) * vte ** 3) * 
                                        jnp.exp(-((vx - Ue(x, y, z)[0])**2 + (vy - Ue(x, y, z)[1])**2 + (vz - Ue(x, y, z)[2])**2) / (2 * vte ** 2))))
    fi = (lambda x, y, z, vx, vy, vz: (1 / (((2 * jnp.pi) ** (3 / 2)) * vti ** 3) * 
                                        jnp.exp(-((vx - Ui(x, y, z)[0])**2 + (vy - Ui(x, y, z)[1])**2 + (vz - Ui(x, y, z)[2])**2) / (2 * vti ** 2))))
    
    return B, E, fe, fi


def simple_example(Lx, Ly):
    """
    I have to add docstrings!
    """
    
    vte = 0.4 # Electron thermal velocity.
    vti = 0.4 # Ion thermal velocity.
    deltaB = 0.2 # In-plane magnetic field amplitude.
    
    # Wavenumbers.
    kx = 2 * jnp.pi / Lx
    ky = 2 * jnp.pi / Ly
    
    # Define elements of 3D Hermite basis.
    Hermite_000 = lambda xi_x, xi_y, xi_z: generate_Hermite_basis(xi_x, xi_y, xi_z, 1, 1, 1, 0)
    Hermite_100 = lambda xi_x, xi_y, xi_z: generate_Hermite_basis(xi_x, xi_y, xi_z, 1, 1, 1, 1)
    
    # Magnetic and electric fields.
    B = lambda x, y, z: jnp.array([-deltaB * jnp.sin(ky * y), deltaB * jnp.sin(2 * kx * x), jnp.ones_like(x)])
    E = lambda x, y, z: jnp.array([jnp.zeros_like(x), jnp.zeros_like(x), jnp.zeros_like(x)])
    
    # Electron and ion distribution functions.
    fe = (lambda x, y, z, vx, vy, vz: 3 * jnp.sin(kx * x) * Hermite_000(vx/vte, vy/vte, vz/vte) + 
          2 * jnp.sin(2 * ky * y) * Hermite_100(vx/vte, vy/vte, vz/vte))
    fi = (lambda x, y, z, vx, vy, vz: 3 * jnp.sin(kx * x) * Hermite_000(vx/vti, vy/vti, vz/vti) + 
          2 * jnp.sin(2 * ky * y) * Hermite_100(vx/vti, vy/vti, vz/vti))
    
    return B, E, fe, fi


def density_perturbation(Lx, Omega_ce, mi_me):
    """
    I have to add docstrings!
    """
    
    vte = jnp.sqrt(0.25 / 2) # Electron thermal velocity.
    vti = vte * jnp.sqrt(1 / mi_me) # Ion thermal velocity.
    
    # Wavenumbers.
    kx = 2 * jnp.pi / Lx
    
    # Magnetic and electric fields.
    B = lambda x, y, z: jnp.array([Omega_ce * jnp.ones_like(x), jnp.zeros_like(y), jnp.zeros_like(z)])
    E = lambda x, y, z: jnp.array([jnp.zeros_like(x), jnp.zeros_like(y), jnp.zeros_like(z)]) # Is this consistent with fe, fi?
    
    # Electron and ion distribution functions.
    fe = (lambda x, y, z, vx, vy, vz: (1 / (((2 * jnp.pi) ** (3 / 2)) * vte ** 3) * 
                                        jnp.exp(-(vx ** 2 + vy ** 2 + vz ** 2) / (2 * vte ** 2))) * 
                                        (1 + 0.3 * jnp.sin(kx * x)))
    fi = (lambda x, y, z, vx, vy, vz: (1 / (((2 * jnp.pi) ** (3 / 2)) * vti ** 3) * 
                                        jnp.exp(-(vx ** 2 + vy ** 2 + vz ** 2) / (2 * vti ** 2))) * 
                                        (1 + 0.3 * jnp.sin(kx * x)))
    
    return B, E, fe, fi


def density_perturbation_solution(Lx, Omega_ce, mi_me):
    """
    I have to add docstrings!
    """
    
    vte = jnp.sqrt(0.25 / 2) # Electron thermal velocity.
    vti = vte * jnp.sqrt(1 / mi_me) # Ion thermal velocity.
    
    # Wavenumbers.
    kx = 2 * jnp.pi / Lx
    
    # Magnetic and electric fields.
    B = lambda x, y, z: jnp.array([Omega_ce * jnp.ones_like(x), jnp.zeros_like(y), jnp.zeros_like(z)])
    E = lambda x, y, z: jnp.array([jnp.zeros_like(x), jnp.zeros_like(y), jnp.zeros_like(z)]) # Is this consistent with fe, fi?
    
    dn = 0.3
    
    # Electron and ion distribution functions.
    fe_exact = (lambda x, y, z, vx, vy, vz: (1 / (((2 * jnp.pi) ** (3 / 2)) * vte ** 3) * 
                                        jnp.exp(-(vx ** 2 + vy ** 2 + vz ** 2) / (2 * vte ** 2))) * 
                                        (1 + dn * jnp.sin(kx * (x - vx * 2.0))))
    fi_exact = (lambda x, y, z, vx, vy, vz: (1 / (((2 * jnp.pi) ** (3 / 2)) * vti ** 3) * 
                                        jnp.exp(-(vx ** 2 + vy ** 2 + vz ** 2) / (2 * vti ** 2))) * 
                                        (1 + dn * jnp.sin(kx * (x - vx * 2.0))))
    
    C0_exact = (lambda t, x: 8 * (1 + dn * jnp.sin(kx * x) * jnp.exp(-(kx * vte * t) ** 2 / 2)))
    
    return B, E, fe_exact, fi_exact, C0_exact


#######################################################################################################################

def Hermite(n, x):
    """
    I have to add docstrings!
    """
    
    n = n.astype(int) # Ensure that n is an integer.
    
    # Add next term in Hermite polynomial. Body function of fori_loop below.
    def add_Hermite_term(m, partial_sum):
        return partial_sum + ((-1)**m / (factorial(m) * factorial(n - 2*m))) * (2*x)**(n - 2*m)
    
    # Return Hermite polynomial of order n.
    return factorial(n) * jax.lax.fori_loop(0, (n // 2) + 1, add_Hermite_term, jnp.zeros_like(x))


def generate_Hermite_basis(xi_x, xi_y, xi_z, Nn, Nm, Np, indices):
    """
    I have to add docstrings!
    """
    
    # Indices below represent order of Hermite polynomials.
    p = jnp.floor(indices / (Nn * Nm)).astype(int)
    m = jnp.floor((indices - p * Nn * Nm) / Nn).astype(int)
    n = (indices - p * Nn * Nm - m * Nn).astype(int)
    
    # Generate element of AW Hermite basis in 3D space.
    Hermite_basis = (Hermite(n, xi_x) * Hermite(m, xi_y) * Hermite(p, xi_z) * 
                  jnp.exp(-(xi_x**2 + xi_y**2 + xi_z**2)) / 
                  jnp.sqrt((jnp.pi)**3 * 2**(n + m + p) * factorial(n) * factorial(m) * factorial(p)))
    
    return Hermite_basis


def compute_C_nmp(f, alpha, u, Nx, Ny, Nz, Lx, Ly, Lz, Nn, Nm, Np, indices):
    """
    I have to add docstrings!
    """
    
    # Indices below represent order of Hermite polynomials.
    p = jnp.floor(indices / (Nn * Nm)).astype(int)
    m = jnp.floor((indices - p * Nn * Nm) / Nn).astype(int)
    n = (indices - p * Nn * Nm - m * Nn).astype(int)
    
    # Generate 6D space for particle distribution function f.
    x = jnp.linspace(0, Lx, Nx)
    y = jnp.linspace(0, Ly, Ny)
    z = jnp.linspace(0, Lz, Nz)
    vx = jnp.linspace(-4, 4, 40) # Possibly define limits in terms of thermal velocity or alpha.
    vy = jnp.linspace(-4, 4, 40)
    vz = jnp.linspace(-4, 4, 40)
    X, Y, Z, Vx, Vy, Vz = jnp.meshgrid(x, y, z, vx, vy, vz, indexing='ij')
    
    # Define variables for Hermite polynomials.
    xi_x = (Vx - u[0]) / alpha[0]
    xi_y = (Vy - u[1]) / alpha[1]
    xi_z = (Vz - u[2]) / alpha[2]
    
    # Compute coefficients of Hermite decomposition of 3D velocity space.
    # Possible improvement: integrate using quadax.quadgk.
    C_nmp = (trapezoid(trapezoid(trapezoid(
                (f(X, Y, Z, Vx, Vy, Vz) * Hermite(n, xi_x) * Hermite(m, xi_y) * Hermite(p, xi_z)) /
                jnp.sqrt(factorial(n) * factorial(m) * factorial(p) * 2 ** (n + m + p)),
                (vx - u[0]) / alpha[0], axis=-3), (vy - u[1]) / alpha[1], axis=-2), (vz - u[2]) / alpha[2], axis=-1))
    
    # def integral_vz(x, y, z, vx, vy):
    #     interval = jnp.array([-jnp.inf, jnp.inf])
    #     integral = quadgk(lambda vz: f(x, y, z, vx, vy, vz) * Hermite(n, (vx - u[0]) / alpha[0]) * 
    #                   Hermite(m, (vy - u[1]) / alpha[1]) * Hermite(p, (vz - u[2]) / alpha[2]) /
    #             jnp.sqrt(factorial(n) * factorial(m) * factorial(p) * 2 ** (n + m + p)), interval)[0]
    #     return integral

    # def integral_vy(x, y, z, vx):
    #     interval = jnp.array([-jnp.inf, jnp.inf])
    #     return quadgk(lambda vy: integral_vz(x, y, z, vx, vy), interval)[0]

    # def C(x, y, z):
    #     interval = jnp.array([-jnp.inf, jnp.inf])
    #     return quadgk(lambda vx: integral_vy(x, y, z, vx), interval)[0]
    
    
    # x = jnp.linspace(0, Lx, Nx)
    # y = jnp.linspace(0, Ly, Ny)
    # z = jnp.linspace(0, Lz, Nz)
    # X, Y, Z = jnp.meshgrid(x, y, z, indexing='ij')
    
    # C_nmp = C(X, Y, Z)
    
    return C_nmp


@partial(jax.jit, static_argnums=[7, 8, 9, 10, 11, 12])
def initialize_system(Omega_ce, mi_me, alpha_s, u_s, Lx, Ly, Lz, Nx, Ny, Nz, Nn, Nm, Np):
    """
    I have to add docstrings!
    """
    
    # Initialize fields and distributions.
    B, E, fe, fi = density_perturbation(Lx, Omega_ce, mi_me)
        
    # Hermite decomposition of dsitribution funcitons.
    Ce_0 = (jax.vmap(
        compute_C_nmp, in_axes=(
            None, None, None, None, None, None, None, None, None, None, None, None, 0))
        (fe, alpha_s[:3], u_s[:3], Nx, Ny, Nz, Lx, Ly, Lz, Nn, Nm, Np, jnp.arange(Nn * Nm * Np)))
    Ci_0 = (jax.vmap(
        compute_C_nmp, in_axes=(
            None, None, None, None, None, None, None, None, None, None, None, None, 0))
        (fi, alpha_s[3:], u_s[3:], Nx, Ny, Nz, Lx, Ly, Lz, Nn, Nm, Np, jnp.arange(Nn * Nm * Np)))

    # Combine Ce_0 and Ci_0 into single array and compute the fast Fourier transform.
    C_0 = jnp.concatenate([Ce_0, Ci_0])
    Ck_0 = fftshift(fftn(C_0, axes=(-3, -2, -1)), axes=(-3, -2, -1))
    
    # Define 3D grid for functions E(x, y, z) and B(x, y, z).
    x = jnp.linspace(0, Lx, Nx)
    y = jnp.linspace(0, Ly, Ny)
    z = jnp.linspace(0, Lz, Nz)
    X, Y, Z = jnp.meshgrid(x, y, z, indexing='ij')
    
    # Combine E and B into single array and compute the fast Fourier transform.
    F_0 = jnp.concatenate([E(X, Y, Z), B(X, Y, Z)])
    Fk_0 = fftshift(fftn(F_0, axes=(-3, -2, -1)), axes=(-3, -2, -1))
    
    return Ck_0, Fk_0


def cross_product(k_vec, F_vec):
    """
    I have to add docstrings!
    """
    
    # Separate vectors into x, y, z components.
    kx, ky, kz = k_vec
    Fx, Fy, Fz = F_vec
    
    # Compute the cross product k x F.
    result_x = ky * Fz - kz * Fy
    result_y = kz * Fx - kx * Fz
    result_z = kx * Fy - ky * Fx

    return jnp.array([result_x, result_y, result_z])


def compute_dCk_s_dt(Ck, Fk, kx_grid, ky_grid, kz_grid, Lx, Ly, Lz, nu, alpha_s, u_s, qs, Omega_cs, Nn, Nm, Np, indices):
    """
    I have to add docstrings!
    """
    
    # Species. s = 0 corresponds to electrons and s = 1 corresponds to ions.
    s = jnp.floor(indices / (Nn * Nm * Np)).astype(int)
    
    # Indices below represent order of Hermite polynomials (they identify the Hermite-Fourier coefficients Ck[n, p, m]).
    p = jnp.floor((indices - s * Nn * Nm * Np) / (Nn * Nm)).astype(int)
    m = jnp.floor((indices - s * Nn * Nm * Np - p * Nn * Nm) / Nn).astype(int)
    n = (indices - s * Nn * Nm * Np - p * Nn * Nm - m * Nn).astype(int)
    
    # Define u, alpha, charge, and gyrofrequency depending on species.
    u = jax.lax.dynamic_slice(u_s, (s * 3,), (3,))
    alpha = jax.lax.dynamic_slice(alpha_s, (s * 3,), (3,))
    q, Omega_c = qs[s], Omega_cs[s]
    
    # Define terms to be used in ODEs below.
    Ck_aux_x = (jnp.sqrt(m * p) * (alpha[2]/alpha[1] - alpha[1]/alpha[2]) * Ck[n + (m-1) * Nn + (p-1) * Nn * Nm + s * Nn * Nm * Np, ...] * jnp.sign(m) * jnp.sign(p) + 
        jnp.sqrt(m * (p + 1)) * (alpha[2] / alpha[1]) * Ck[n + (m-1) * Nn + (p+1) * Nn * Nm + s * Nn * Nm * Np, ...] * jnp.sign(m) * jnp.sign(Np - p - 1) - 
        jnp.sqrt((m + 1) * p) * (alpha[1] / alpha[2]) * Ck[n + (m+1) * Nn + (p-1) * Nn * Nm + s * Nn * Nm * Np, ...] * jnp.sign(p) * jnp.sign(Nm - m - 1) + 
        jnp.sqrt(2 * m) * (u[2] / alpha[1]) * Ck[n + (m-1) * Nn + p * Nn * Nm + s * Nn * Nm * Np, ...] * jnp.sign(m) - 
        jnp.sqrt(2 * p) * (u[1] / alpha[2]) * Ck[n + m * Nn + (p-1) * Nn * Nm + s * Nn * Nm * Np, ...] * jnp.sign(p)) 

    Ck_aux_y = (jnp.sqrt(n * p) * (alpha[0]/alpha[2] - alpha[2]/alpha[0]) * Ck[n-1 + m * Nn + (p-1) * Nn * Nm + s * Nn * Nm * Np, ...] * jnp.sign(n) * jnp.sign(p) + 
        jnp.sqrt((n + 1) * p) * (alpha[0] / alpha[2]) * Ck[n+1 + m * Nn + (p-1) * Nn * Nm + s * Nn * Nm * Np, ...] * jnp.sign(p) * jnp.sign(Nn - n - 1) - 
        jnp.sqrt(n * (p + 1)) * (alpha[2] / alpha[0]) * Ck[n-1 + m * Nn + (p+1) * Nn * Nm + s * Nn * Nm * Np, ...] * jnp.sign(n) * jnp.sign(Np - p - 1) + 
        jnp.sqrt(2 * p) * (u[0] / alpha[2]) * Ck[n + m * Nn + (p-1) * Nn * Nm + s * Nn * Nm * Np, ...] * jnp.sign(p) - 
        jnp.sqrt(2 * n) * (u[2] / alpha[0]) * Ck[n-1 + m * Nn + p * Nn * Nm + s * Nn * Nm * Np, ...] * jnp.sign(n))
    
    Ck_aux_z = (jnp.sqrt(n * m) * (alpha[1]/alpha[0] - alpha[0]/alpha[1]) * Ck[n-1 + (m-1) * Nn + p * Nn * Nm + s * Nn * Nm * Np, ...] * jnp.sign(n) * jnp.sign(m) + 
        jnp.sqrt(n * (m + 1)) * (alpha[1] / alpha[0]) * Ck[n-1 + (m+1) * Nn + p * Nn * Nm + s * Nn * Nm * Np, ...] * jnp.sign(n) * jnp.sign(Nm - m - 1) - 
        jnp.sqrt((n + 1) * m) * (alpha[0] / alpha[1]) * Ck[n+1 + (m-1) * Nn + p * Nn * Nm + s * Nn * Nm * Np, ...] * jnp.sign(m) * jnp.sign(Nn - n - 1) + 
        jnp.sqrt(2 * n) * (u[1] / alpha[0]) * Ck[n-1 + m * Nn + p * Nn * Nm + s * Nn * Nm * Np, ...] * jnp.sign(n) - 
        jnp.sqrt(2 * m) * (u[0] / alpha[1]) * Ck[n + (m-1) * Nn + p * Nn * Nm + s * Nn * Nm * Np, ...] * jnp.sign(m))
    
    # Define "unphysical" collision operator to eliminate recurrence.
    # Col = -nu * ((n * (n - 1) * (n - 2)) / ((Nn - 1) * (Nn - 2) * (Nn - 3)) + 
    #              (m * (m - 1) * (m - 2)) / ((Nm - 1) * (Nm - 2) * (Nm - 3)) +
    #              (p * (p - 1) * (p - 2)) / ((Np - 1) * (Np - 2) * (Np - 3))) * Ck[n + m * Nn + p * Nn * Nm + s * Nn * Nm * Np, ...]
    
    Col = 0
    
    # Define ODEs for Hermite-Fourier coefficients.
    # Clossure is achieved by setting to zero coefficients with index out of range.
    dCk_s_dt = (- (kx_grid * 1j / Lx) * alpha[0] * (
        jnp.sqrt((n + 1) / 2) * Ck[n+1 + m * Nn + p * Nn * Nm + s * Nn * Nm * Np, ...] * jnp.sign(Nn - n - 1) +
        jnp.sqrt(n / 2) * Ck[n-1 + m * Nn + p * Nn * Nm + s * Nn * Nm * Np, ...] * jnp.sign(n) +
        (u[0] / alpha[0]) * Ck[n + m * Nn + p * Nn * Nm + s * Nn * Nm * Np, ...]
    ) - (ky_grid * 1j / Ly) * alpha[1] * (
        jnp.sqrt((m + 1) / 2) * Ck[n + (m+1) * Nn + p * Nn * Nm + s * Nn * Nm * Np, ...] * jnp.sign(Nm - m - 1) +
        jnp.sqrt(m / 2) * Ck[n + (m-1) * Nn + p * Nn * Nm + s * Nn * Nm * Np, ...] * jnp.sign(m) +
        (u[1] / alpha[1]) * Ck[n + m * Nn + p * Nn * Nm + s * Nn * Nm * Np, ...]
    ) - (kz_grid * 1j / Lz) * alpha[2] * (
        jnp.sqrt((p + 1) / 2) * Ck[n + m * Nn + (p+1) * Nn * Nm + s * Nn * Nm * Np, ...] * jnp.sign(Np - p - 1) +
        jnp.sqrt(p / 2) * Ck[n + m * Nn + (p-1) * Nn * Nm + s * Nn * Nm * Np, ...] * jnp.sign(p) +
        (u[2] / alpha[2]) * Ck[n + m * Nn + p * Nn * Nm + s * Nn * Nm * Np, ...]
    ) + q * Omega_c * (
        (jnp.sqrt(2 * n) / alpha[0]) * convolve(Fk[0, ...], Ck[n-1 + m * Nn + p * Nn * Nm + s * Nn * Nm * Np, ...] * jnp.sign(n), mode='same') +
        (jnp.sqrt(2 * m) / alpha[1]) * convolve(Fk[1, ...], Ck[n + (m-1) * Nn + p * Nn * Nm + s * Nn * Nm * Np, ...] * jnp.sign(m), mode='same') +
        (jnp.sqrt(2 * p) / alpha[2]) * convolve(Fk[2, ...], Ck[n + m * Nn + (p-1) * Nn * Nm + s * Nn * Nm * Np, ...] * jnp.sign(p), mode='same')
    ) + q * Omega_c * (
        convolve(Fk[3, ...], Ck_aux_x, mode='same') + 
        convolve(Fk[4, ...], Ck_aux_y, mode='same') + 
        convolve(Fk[5, ...], Ck_aux_z, mode='same')
    ) + Col)
    
    return dCk_s_dt

@partial(jax.jit, static_argnums=[10, 11, 12, 13, 14, 15, 16])
def ode_system(Ck_Fk, t, qs, nu, Omega_cs, alpha_s, u_s, Lx, Ly, Lz, Nx, Ny, Nz, Nn, Nm, Np, Ns):     
    
    # Define wave vectors.
    kx = (jnp.arange(-Nx//2, Nx//2) + 1) * 2 * jnp.pi
    ky = (jnp.arange(-Ny//2, Ny//2) + 1) * 2 * jnp.pi
    kz = (jnp.arange(-Nz//2, Nz//2) + 1) * 2 * jnp.pi

    # Create 3D grids of kx, ky, kz.
    kx_grid, ky_grid, kz_grid = jnp.meshgrid(kx, ky, kz, indexing='ij')
    
    # Separate between initial conditions for distribution functions (coefficients Ck)
    # and electric and magnetic fields (coefficients Fk).
    Ck = Ck_Fk[:(-6 * Nx * Ny * Nz)].reshape(Ns * Nn * Nm * Np, Nx, Ny, Nz)
    Fk = Ck_Fk[(-6 * Nx * Ny * Nz):].reshape(6, Nx, Ny, Nz)
    
    # Vectorize over n, m, p, and s to generate ODEs for all coefficients Ck.
    dCk_s_dt = (jax.vmap(
        compute_dCk_s_dt, 
        in_axes=(None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, 0))
        (Ck, Fk, kx_grid, ky_grid, kz_grid, Lx, Ly, Lz, nu, alpha_s, u_s, qs, Omega_cs, Nn, Nm, Np, jnp.arange(Nn * Nm * Np * Ns)))
        
    # Generate ODEs for Bk and Ek.
    dBk_dt = - 1j * cross_product(jnp.array([kx_grid/Lx, ky_grid/Ly, kz_grid/Lz]), Fk[:3, ...])
    dEk_dt = 1j * cross_product(jnp.array([kx_grid/Lx, ky_grid/Ly, kz_grid/Lz]), Fk[3:, ...]) - \
             (1 / Omega_cs[0]) * (qs[0] * alpha_s[0] * alpha_s[1] * alpha_s[2] * (
             (1 / jnp.sqrt(2)) * jnp.array([alpha_s[0] * Ck[1, ...],
                                            alpha_s[1] * Ck[Nn + 1, ...],
                                            alpha_s[2] * Ck[Nn * Nm + 1, ...]]) + 
                                 jnp.array([u_s[0] * Ck[0, ...],
                                            u_s[1] * Ck[0, ...],
                                            u_s[2] * Ck[0, ...]])) + \
                                  qs[1] * alpha_s[3] * alpha_s[4] * alpha_s[5] * (
             (1 / jnp.sqrt(2)) * jnp.array([alpha_s[3] * Ck[Nn * Nm * Np + 1, ...],
                                            alpha_s[4] * Ck[Nn + Nn * Nm * Np + 1, ...],
                                            alpha_s[5] * Ck[Nn * Nm + Nn * Nm * Np + 1, ...]]) + 
                                 jnp.array([u_s[3] * Ck[Nn * Nm * Np, ...],
                                            u_s[4] * Ck[Nn * Nm * Np, ...],
                                            u_s[5] * Ck[Nn * Nm * Np, ...]])))

    # Combine dC/dt and dF/dt into a single array and flatten it into a 1D array for an ODE solver.
    dFk_dt = jnp.concatenate([dEk_dt, dBk_dt])
    dy_dt = jnp.concatenate([dCk_s_dt.flatten(), dFk_dt.flatten()])
    
    return dy_dt

@partial(jax.jit, static_argnums=[7, 8, 9, 10, 11, 12, 13, 14, 15])
def anti_transform(Ck, Fk, alpha_s, u_s, Lx, Ly, Lz, Nx, Ny, Nz, Nvx, Nvy, Nvz, Nn, Nm, Np):
    
    F = ifftn(ifftshift(Fk, axes=(-3, -2, -1)), axes=(-3, -2, -1))
    E, B = F[:, :3, ...], F[:, 3:, ...]
        
    C = ifftn(ifftshift(Ck, axes=(-3, -2, -1)), axes=(-3, -2, -1))
    
    Ce = C[:, :(Nn * Nm * Np), ...]
    Ci = C[:, (Nn * Nm * Np):, ...]
    
    # x = jnp.linspace(0, Lx, Nx)
    # y = jnp.linspace(0, Ly, Ny)
    # z = jnp.linspace(0, Lz, Nz)
    # vx = jnp.linspace(-5, 5, Nvx)
    # vy = jnp.linspace(-5, 5, Nvy)
    # vz = jnp.linspace(-5, 5, Nvz)
    # X, Y, Z, Vx, Vy, Vz = jnp.meshgrid(x, y, z, vx, vy, vz, indexing='ij')
    
    # xi_x = (Vx - u_s[0]) / alpha_s[0]
    # xi_y = (Vy - u_s[1]) / alpha_s[1]
    # xi_z = (Vz - u_s[2]) / alpha_s[2]
    
    # full_Hermite_basis_e = jax.vmap(generate_Hermite_basis, in_axes=(None, None, None, None, None, None, 0))(xi_x, xi_y, xi_z, Nn, Nm, Np, jnp.arange(Nn * Nm * Np))
    
    # xi_x = (Vx - u_s[3]) / alpha_s[3]
    # xi_y = (Vy - u_s[4]) / alpha_s[4]
    # xi_z = (Vz - u_s[5]) / alpha_s[5]
    
    # full_Hermite_basis_i = jax.vmap(generate_Hermite_basis, in_axes=(None, None, None, None, None, None, 0))(xi_x, xi_y, xi_z, Nn, Nm, Np, jnp.arange(Nn * Nm * Np))
    
    # shape_C_expanded = Ce.shape + (Nvx, Nvy, Nvz)
    
    # Ce_expanded = jnp.expand_dims(Ce, (4, 5, 6))
    # Ci_expanded = jnp.expand_dims(Ci, (4, 5, 6))
    
    # Ce_expanded = jnp.broadcast_to(Ce_expanded, shape_C_expanded)
    # Ci_expanded = jnp.broadcast_to(Ci_expanded, shape_C_expanded)
    
    # fe = jnp.array([jnp.sum(Ce_expanded[i, ...] * full_Hermite_basis_e, axis=0) for i in jnp.arange(Ce.shape[0])])
    # fi = jnp.array([jnp.sum(Ci_expanded[i, ...] * full_Hermite_basis_i, axis=0) for i in jnp.arange(Ce.shape[0])])
    
    # The electron and ion energy formulas below assume that us = 0. Generalize them.
    electron_energy_dens = 0.5 * ((3 / 2) * Ce[:, 0, ...] + Ce[:, 2, ...] + Ce[:, Nn + 2, ...] + Ce[:, Nn * Nm + 2, ...])
    ion_energy_dens = 0.5 * ((3 / 2) * Ci[:, 0, ...] + Ci[:, 2, ...] + Ci[:, Nn + 2, ...] + Ci[:, Nn * Nm + 2, ...])
     
    plasma_energy = jnp.mean(electron_energy_dens[:, :, 1, 1], axis=1) + jnp.mean(ion_energy_dens[:, :, 1, 1], axis=1)
    
    EM_energy = (jnp.mean((E[:, 0, :, 1, 1] ** 2 + E[:, 1, :, 1, 1] ** 2 + E[:, 2, :, 1, 1] ** 2 + 
                           B[:, 0, :, 1, 1] ** 2 + B[:, 1, :, 1, 1] ** 2 + B[:, 2, :, 1, 1] ** 2) / 2, axis=1))
    
    return B, E, Ce, Ci, plasma_energy, EM_energy

def main():
    # Load simulation parameters.
    with open('plasma_parameters_density_perturbation.json', 'r') as file:
        parameters = json.load(file)
    
    # Unpack parameters.
    Nx, Ny, Nz = parameters['Nx'], parameters['Ny'], parameters['Nz']
    Nvx, Nvy, Nvz = parameters['Nvx'], parameters['Nvy'], parameters['Nvz']
    Lx, Ly, Lz = parameters['Lx'], parameters['Ly'], parameters['Lz']
    Nn, Nm, Np, Ns = parameters['Nn'], parameters['Nm'], parameters['Np'], parameters['Ns']
    mi_me = parameters['mi_me']
    Omega_cs = parameters['Omega_ce'] * jnp.array([1.0, 1.0 / mi_me])
    qs = jnp.array(parameters['qs'])
    alpha_s = jnp.array(parameters['alpha_s'])
    u_s = jnp.array(parameters['u_s'])
    nu = parameters['nu']

    # Load initial conditions.
    Ck_0, Fk_0 = initialize_system(Omega_cs[0], mi_me, alpha_s, u_s, Lx, Ly, Lz, Nx, Ny, Nz, Nn, Nm, Np)

    # Combine initial conditions.
    initial_conditions = jnp.concatenate([Ck_0.flatten(), Fk_0.flatten()])

    # Define the time array.
    t = jnp.linspace(0, 10, 11)

    dy_dt = partial(ode_system, qs=qs, nu=nu, Omega_cs=Omega_cs, alpha_s=alpha_s, u_s=u_s, Lx=Lx, Ly=Ly, Lz=Lz, Nx=Nx, Ny=Ny, Nz=Nz, Nn=Nn, Nm=Nm, Np=Np, Ns=Ns)

    # Solve the ODE system (I have to rewrite this part of the code).
    result = odeint(dy_dt, initial_conditions, t)
    
    Ck = result[:,:(-6 * Nx * Ny * Nz)].reshape(len(t), Ns * Nn * Nm * Np, Nx, Ny, Nz)
    Fk = result[:,(-6 * Nx * Ny * Nz):].reshape(len(t), 6, Nx, Ny, Nz)
    
    # Define wave vectors.
    kx = (jnp.arange(-Nx//2, Nx//2) + 1) * 2 * jnp.pi
    ky = (jnp.arange(-Ny//2, Ny//2) + 1) * 2 * jnp.pi
    kz = (jnp.arange(-Nz//2, Nz//2) + 1) * 2 * jnp.pi
    
    # Create 3D grids of kx, ky, kz.
    kx_grid, ky_grid, kz_grid = jnp.meshgrid(kx, ky, kz, indexing='ij')
    
    divBk2_mean = jnp.mean(jnp.array([kx_grid * Fk[i, 3, ...] + ky_grid * Fk[i, 4, ...] + kz_grid * Fk[i, 5, ...] for i in jnp.arange(len(t))]) ** 2, axis=[1, 2, 3])
    
    B, E, Ce, Ci, plasma_energy, EM_energy = anti_transform(Ck, Fk, alpha_s, u_s, Lx, Ly, Lz, Nx, Ny, Nz, Nvx, Nvy, Nvz, Nn, Nm, Np)
    
    Cn002 = jnp.mean(Ce[:, :Nn, ...], axis=[2, 3, 4])
    
    B_exact, E_exact, fe_exact, fi_exact, C0_exact = density_perturbation_solution(Lx, Omega_cs[0], mi_me)
    
    x = jnp.linspace(0, Lx, Nx)
    
    T, X = jnp.meshgrid(t, x, indexing='ij')
    
    C0_x_t_exact = C0_exact(T, X)
    
    
    # Plot magnetic field.
    plt.plot(t, jnp.sqrt(jnp.mean(E[:, 0, :, 1, 1].real ** 2, axis=1)), label='$B_{x,rms}$', linestyle='-', color='red')
    plt.plot(t, jnp.sqrt(jnp.mean(E[:, 1, :, 1, 1].real ** 2, axis=1)), label='$B_{y,rms}$', linestyle='--', color='blue')
    plt.plot(t, jnp.sqrt(jnp.mean(E[:, 2, :, 1, 1].real ** 2, axis=1)), label='$B_{z,rms}$', linestyle='-.', color='green')

    plt.xlabel('$t\omega_{pe}$')
    plt.ylabel('$B_{rms}$')
    plt.title('Magnetic field vs. Time')

    plt.legend()

    plt.show()
    
    # C0 vs t.
    
    plt.figure(figsize=(8, 6))
    plt.plot(x, Ce[0 ,0, :, 1, 1].real, label='Approx. solution, t\omega_{pe} = 0', linestyle='-', color='red')
    plt.plot(x, C0_x_t_exact[0, :].real, label='Exact solution, t\omega_{pe} = 0', linestyle='--', color='black')
    plt.plot(x, Ce[5 ,0, :, 1, 1].real, label='Approx. solution, t\omega_{pe} = 5', linestyle='-', color='blue')
    plt.plot(x, C0_x_t_exact[5, :].real, label='Exact solution, t\omega_{pe} = 5', linestyle=':', color='black')
    plt.plot(x, Ce[10 ,0, :, 1, 1].real, label='Approx. solution, t\omega_{pe} = 10', linestyle='-', color='green')
    plt.plot(x, C0_x_t_exact[10, :].real, label='Exact solution, t\omega_{pe} = 10', linestyle='-.', color='black')

    plt.xlabel(r'$x/d_e$', fontsize=16)
    plt.ylabel(r'$C_{e, 0}$', fontsize=16)
    plt.xlim((0,3))
    plt.ylim((4,12))
    plt.title(r'$\nu = 0$', fontsize=16)
    plt.legend()

    plt.show()
    
    # Hermite coefficients at fixed times.
    
    plt.plot(jnp.arange(12), jnp.mean(jnp.abs(Ce[0 , :, ...]) ** 2, axis=[-3, -2, -1]), label='Approx. solution, t\omega_{pe} = 0', linestyle='-', color='red')
    plt.plot(jnp.arange(12), jnp.mean(jnp.abs(Ce_exact_0) ** 2, axis=[-3, -2, -1]), label='Exact solution, t\omega_{pe} = 0', linestyle='--', color='black')
    plt.plot(jnp.arange(12), jnp.mean(jnp.abs(Ce[5 , :, ...]) ** 2, axis=[-3, -2, -1]), label='Approx. solution, t\omega_{pe} = 5', linestyle='-', color='blue')
    plt.plot(jnp.arange(12), jnp.mean(jnp.abs(Ce_exact_5) ** 2, axis=[-3, -2, -1]), label='Exact solution, t\omega_{pe} = 5', linestyle=':', color='black')
    plt.plot(jnp.arange(12), jnp.mean(jnp.abs(Ce[10 , :, ...]) ** 2, axis=[-3, -2, -1]), label='Approx. solution, t\omega_{pe} = 10', linestyle='-', color='green')
    plt.plot(jnp.arange(12), jnp.mean(jnp.abs(Ce_exact_10) ** 2, axis=[-3, -2, -1]), label='Exact solution, t\omega_{pe} = 10', linestyle='-.', color='black')
    plt.xlabel(r'$n$', fontsize=16)
    plt.ylabel(r'$\langle|C_{e, n}|^2\rangle$', fontsize=16)
    plt.title(r'$\nu = 0$', fontsize=16)
    # plt.legend()
    plt.yscale('log')
    plt.show()
    
    

if __name__ == "__main__":
    main()
