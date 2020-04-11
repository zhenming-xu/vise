# -*- coding: utf-8 -*-

import os
from pathlib import Path
import pytest
import tempfile

from pymatgen import Structure

from vise.input_set.input_set import ViseInputSet
from vise.input_set.xc import Xc
from vise.util.testing import ViseTest


@pytest.fixture
def input_set():
    structure = Structure(
        lattice=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        species=["H"],
        coords=[[0.0, 0.0, 0.0]])
    return ViseInputSet.make_input(structure=structure, xc=Xc.hse)


def test_incar(input_set):
    expected = """# algorithm
ALGO  =  D

# accuracy
PREC   =  N
LREAL  =  False
EDIFF  =  1e-07
ENCUT  =  325.0
LASPH  =  True
NELM   =  100

# ionic relaxation
ISIF    =  3
IBRION  =  2
EDIFFG  =  -0.005
NSW     =  50
TIME    =  0.4

# occupation
ISMEAR  =  0
SIGMA   =  0.1

# spin
ISPIN  =  1

# IO control
LWAVE   =  True
LCHARG  =  False

# analyzer
LORBIT  =  12

# hybrid functional
LHFCALC   =  True
PRECFOCK  =  Fast
AEXX      =  0.25
HFSCREEN  =  0.208

# parallel
KPAR  =  4"""

    assert str(input_set.incar) == expected


def test_kpoints(input_set):
    expected = """Generated by vise. Mode: primitive, kpt density: 2.5, factor: 1.
0
Gamma
16 16 16
0.5 0.5 0.5
"""
    assert str(input_set.kpoints) == expected


def test_poscar(input_set):
    expected = """H1
1.0
1.000000 0.000000 0.000000
0.000000 1.000000 0.000000
0.000000 0.000000 1.000000
H
1
direct
0.000000 0.000000 0.000000 H
"""
    assert str(input_set.poscar) == expected


def test_potcar(input_set):
    assert input_set.potcar.symbols == ["H"]


def test_write(input_set):
    with tempfile.TemporaryDirectory() as tmp_dirname:
        os.chdir(tmp_dirname)
        input_set.write_input(output_dir=tmp_dirname)
        os.remove("INCAR")
        os.remove("POSCAR")
        os.remove("POTCAR")
        os.remove("KPOINTS")
        os.remove("vise.json")
        Path.cwd()  # may be safer to go back to cwd


def test_dict(input_set):
    expected = input_set.as_dict()
    actual = ViseInputSet.from_dict(expected).as_dict()
    assert actual == expected


# def test_msonable():
#     self.assertMSONable(self.input_set)
