# -*- coding: utf-8 -*-
#  Copyright (c) 2020. Distributed under the terms of the MIT License.

import numpy as np

from pymatgen.electronic_structure.boltztrap2 import VasprunBSLoader, \
    BztInterpolator, BztTransportProperties
from vise.analyzer.effective_mass import EffectiveMass


def make_effective_mass(vasprun, temp, concentrations, band_gap):
    vl = VasprunBSLoader(vasprun)
    energy_range = band_gap / 2 + 2.0
    bi = BztInterpolator(vl, energy_range=energy_range)
    btp = BztTransportProperties(bi, temp_r=np.array([temp]))
    btp.compute_properties_doping(concentrations)

    return EffectiveMass(p=btp.Effective_mass_doping["p"].tolist()[0],
                         n=btp.Effective_mass_doping["n"].tolist()[0],
                         concentrations=concentrations)