# -*- coding: utf-8 -*-

#  Copyright (c) 2020. Distributed under the terms of the MIT License.

import re
from collections import defaultdict

from pymatgen import Spin
from pymatgen.electronic_structure.plotter import BSPlotter
from pymatgen.io.vasp import Vasprun
from pymatgen.util.string import latexify

from vise.analyzer.plot_band import BandPlotter, BandInfo, XTicks, BandEdge


def greek_to_unicode(label: str) -> str:
    d = {"GAMMA": "Γ", "SIGMA": "Σ", "DELTA": "Δ"}
    for k, v in d.items():
        label = label.replace(k, v)
    return label


def italic_to_roman(label: str) -> str:
    return re.sub(r"([A-Z])_([0-9])", r"{\\rm \1}_\2", label)


class VaspBandPlotter(BandPlotter):
    def __init__(self,
                 vasprun: Vasprun,
                 kpoints_filename: str,
                 reference_energy: float = None,
                 ):

        self._bs = vasprun.get_band_structure(kpoints_filename, line_mode=True)
        self._plot_data = BSPlotter(self._bs).bs_plot_data(zero_to_efermi=False)
        self._composition = vasprun.final_structure.composition

        super().__init__(band_info_set=[self._band_info],
                         distances_by_branch=self._plot_data["distances"],
                         x_ticks=self._x_ticks,
                         y_range=[-10, 10],
                         reference_energy=reference_energy,
                         title=self._title)

    @property
    def _band_info(self):
        return BandInfo(band_energies=self._order_changed_energies,
                        band_edge=self._band_edge,
                        fermi_level=self._bs.efermi)

    @property
    def _order_changed_energies(self):
        result = defaultdict(list)
        for idx, branch_energies in enumerate(self._plot_data["energies"]):
            for spin, energy_of_a_spin in branch_energies.items():
                spin = Spin.up if spin == "1" else Spin.down
                result[spin].append(energy_of_a_spin)

        return dict(result)

    @property
    def _x_ticks(self):
        labels = self._sanitize_labels(self._plot_data["ticks"]["label"])
        distances = self._plot_data["ticks"]["distance"]
        return XTicks(labels=labels, distances=distances)

    @property
    def _band_edge(self):
        if self._bs.is_metal():
            return None
        else:
            return BandEdge(
                vbm=self._plot_data["vbm"][0][1],
                cbm=self._plot_data["cbm"][0][1],
                vbm_distances=[i[0] for i in self._plot_data["vbm"]],
                cbm_distances=[i[0] for i in self._plot_data["cbm"]])

    @property
    def _title(self):
        return latexify(self._composition.reduced_formula)

    @staticmethod
    def _sanitize_labels(labels):
        return [italic_to_roman(greek_to_unicode(label)) for label in labels]