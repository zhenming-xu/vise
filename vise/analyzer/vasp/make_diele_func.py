# -*- coding: utf-8 -*-
#  Copyright (c) 2020. Distributed under the terms of the MIT License.
from multiprocessing import Pool

from pymatgen.io.vasp import Vasprun, Outcar
from vise.analyzer.dielectric_function import DieleFuncData
from vise.analyzer.vasp.band_edge_properties import VaspBandEdgeProperties
from math import sqrt, pi
from typing import List
import multiprocessing as multi

import numpy as np


def make_diele_func(vasprun: Vasprun,
                    outcar: Outcar,
                    corrected_band_gap: float = None):
    energies, real, imag = vasprun.dielectric_data["density"]
    real, imag = np.array(real), np.array(imag)
    band_gap = VaspBandEdgeProperties(vasprun, outcar).band_gap

    if corrected_band_gap is not None:
        shift = corrected_band_gap - band_gap
        band_gap = corrected_band_gap
        imag = imag_shift(imag, energies, band_gap, shift)
        real = kramers_kronig_trans(imag, energies)

    return DieleFuncData(energies, real, imag, band_gap)


def imag_shift(diele_func_imag: np.ndarray,
               energies: List[float],
               band_gap: float,
               shift: float):

    assert shift > 0
    result = []
    for energy_grid in energies:
        old_e = energy_grid - shift
        right_idx = np.argwhere(energies > old_e)[0][0]
        left_e, right_e = energies[right_idx - 1], energies[right_idx]
        # linear interpolation
        left_ratio = (right_e - old_e) / (right_e - left_e)

        inner_result = []
        for imag_idx in range(6):
            if energy_grid < band_gap:
                inner_result.append(0.0)
            else:
                old_diele = (diele_func_imag[right_idx - 1][imag_idx] * left_ratio +
                             diele_func_imag[right_idx][imag_idx] * (1 - left_ratio))
                inner_result.append(old_diele * (energy_grid - shift) / energy_grid)

        result.append(inner_result)

    return np.array(result)


def kramers_kronig_trans(diele_func_imag: np.ndarray,
                         energies: List[float],
                         ita=0.1):
    mesh = energies[1] - energies[0]
    result = []
    ee2ss = [[e ** 2 - energy_grid ** 2 for e in energies] for energy_grid in energies]
    for imag_idx in [0]:
        imags = diele_func_imag[:, imag_idx]
        inner_result = []
        for ee2s in ee2ss:
            integrals = [e * imag * ee2 / (ee2 ** 2 + ita ** 2)
                         for e, ee2, imag in zip(energies, ee2s, imags)]
            inner_result.append(1 + sum(integrals) * mesh * 2 / pi)

        result.append(inner_result)

    return np.array(result).T

