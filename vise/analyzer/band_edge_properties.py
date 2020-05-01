# -*- coding: utf-8 -*-
#  Copyright (c) 2020. Distributed under the terms of the MIT License.

from dataclasses import dataclass
from typing import List, Dict

import numpy as np
from pymatgen.electronic_structure.core import Spin
from vise.defaults import defaults


@dataclass()
class BandEdge:
    energy: float
    spin: Spin = None
    band_index: int = None
    kpoint_coords: List[float] = None

    def is_direct(self, other: "BandEdge"):
        return (self.spin == other.spin and
                self.kpoint_coords == other.kpoint_coords)


class BandEdgeProperties:
    def __init__(self,
                 eigenvalues: Dict[Spin, np.ndarray],
                 nelect: float,
                 magnetization: float,
                 kpoints: List[List[float]],
                 integer_criterion: float = defaults.integer_criterion):

        assert 0 < integer_criterion < 0.5

        # [Spin][k-point_idx][band_idx] = eigenvalue
        self._eigenvalues = eigenvalues
        self._nelect = nelect
        #  In Bohr magneton.
        self._magnetization = magnetization
        self._kpoints = kpoints
        self._integer_criterion = integer_criterion

        self._calculate_vbm_cbm()

        if self._is_metal():
            self.vbm_info = None
            self.cbm_info = None

    def _calculate_vbm_cbm(self):
        self.vbm_info = BandEdge(float("-inf"))
        self.cbm_info = BandEdge(float("inf"))
        for spin, eigenvalues in self._eigenvalues.items():
            # ho = highest occupied
            ho_eigenvalue = np.amax(eigenvalues[:, self._ho_band_index(spin)])
            if ho_eigenvalue > self.vbm_info.energy:
                self.vbm_info = self.band_edge(
                    eigenvalues, self._ho_band_index(spin), ho_eigenvalue, spin)

            # lu = lowest unoccupied
            lu_band_index = self._ho_band_index(spin) + 1
            lu_eigenvalue = np.amin(eigenvalues[:, lu_band_index])
            if lu_eigenvalue < self.cbm_info.energy:
                self.cbm_info = self.band_edge(
                    eigenvalues, lu_band_index, lu_eigenvalue, spin)

    def band_edge(self, eigenvalues, band_index, eigenvalue, spin):
        k_index = np.where(eigenvalues[:, band_index] == eigenvalue)[0][0]
        return BandEdge(eigenvalue, spin, band_index, self._kpoints[k_index])

    def _ho_band_index(self, spin):
        if spin == Spin.up:
            num_occupied_band = (self._nelect + self._magnetization) / 2
        else:
            num_occupied_band = (self._nelect - self._magnetization) / 2

        return round(num_occupied_band) - 1

    def _is_metal(self):
        nelect_frac = abs(round(self._nelect) - self._nelect)
        is_nelect_frac = nelect_frac > self._integer_criterion

        mag_frac = abs(round(self._magnetization) - self._magnetization)
        is_mag_frac = mag_frac > self._integer_criterion

        is_vbm_higher_than_cbm = self.vbm_info.energy > self.cbm_info.energy

        return is_nelect_frac or is_mag_frac or is_vbm_higher_than_cbm

    @property
    def is_direct(self):
        return self.vbm_info.is_direct(self.cbm_info) if self.vbm_info else None

    @property
    def band_gap(self):
        return self.cbm_info.energy - self.vbm_info.energy if self.vbm_info else None

