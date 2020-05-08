# -*- coding: utf-8 -*-
#  Copyright (c) 2020. Distributed under the terms of the MIT License.
import os
import shutil

from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from vise.cli.main import parse_args
from vise.util.testing import ViseTest
from vise.defaults import defaults
from vise.input_set.task import Task
from vise.input_set.xc import Xc

parent_dir = Path(__file__).parent


def test_get_poscars_wo_options():
    actual = parse_args(["gp"])
    # func is a pointer so need to point the same address.
    expected = Namespace(
        poscar="POSCAR",
        mpid=None,
        func=actual.func)
    assert actual == expected


def test_get_poscars_w_options():
    parsed_args = parse_args(["gp",
                              "-p", "a",
                              "-m", "123"])

    expected = Namespace(
        poscar="a",
        mpid="123",
        func=parsed_args.func)
    assert parsed_args == expected


def test_vasp_set_wo_options():
    parsed_args = parse_args(["vs"])
    # func is a pointer so need to point the same address.
    expected = Namespace(
        poscar="POSCAR",
        task=defaults.task,
        xc=defaults.xc,
        kpt_density=defaults.kpoint_density,
        overridden_potcar=defaults.overridden_potcar,
        charge=0.0,
        user_incar_settings=None,
        prev_dir=None,
        options=None,
        uniform_kpt_mode=False,
        file_transfer_type=None,
        )
    assert parsed_args == expected


def test_vasp_set_w_options():
    parsed_args = parse_args(["vs",
                              "--poscar", "POSCAR-tmp",
                              "-t", "band",
                              "-x", "pbesol",
                              "-k", "4.2",
                              "--potcar", "Mg_pv", "O_h",
                              "-c", "10",
                              "--user_incar_settings", "LREAD", "F",
                              "-d", "c",
                              "--options", "encut", "800",
                              "--uniform_kpt_mode",
                              "--file_transfer_type", "WAVECAR", "C",
                              ])

    expected = Namespace(
        poscar="POSCAR-tmp",
        task=Task.band,
        xc=Xc.pbesol,
        kpt_density=4.2,
        overridden_potcar=["Mg_pv", "O_h"],
        charge=10.0,
        user_incar_settings=["LREAD", "F"],
        prev_dir=Path("c"),
        options=["encut", "800"],
        uniform_kpt_mode=True,
        file_transfer_type=["WAVECAR", "C"]
    )

    assert parsed_args == expected


