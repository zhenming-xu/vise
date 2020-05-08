# -*- coding: utf-8 -*-
#  Copyright (c) 2020. Distributed under the terms of the MIT License.

from copy import deepcopy
import pytest
from pathlib import Path

from argparse import Namespace
from pymatgen.core.structure import Structure

from vise.cli.main_functions import get_poscar_from_mp, VaspSet, plot_band

from vise.input_set.input_options import CategorizedInputOptions
from vise.input_set.vasp_input_files import VaspInputFiles
from vise.defaults import defaults
from vise.input_set.task import Task
from vise.input_set.xc import Xc
from vise.input_set.kpoints_mode import KpointsMode



def test_get_poscar_from_mp(tmpdir):
    args = Namespace(mpid="mp-110", poscar="POSCAR")

    tmpdir.chdir()
    get_poscar_from_mp(args)
    file = tmpdir.join("POSCAR")
    expected = """Mg1
1.0
2.922478 0.000000 -1.033252
-1.461239 2.530940 -1.033252
0.000000 0.000000 3.099756
Mg
1
direct
0.000000 0.000000 0.000000 Mg
"""
    assert file.read() == expected


default_option_args = {"poscar": "POSCAR",
                       "task": Task.structure_opt,
                       "xc": Xc.pbe,
                       "kpt_density": 1.0,
                       "overridden_potcar": ["Mn_pv"],
                       "charge": 2.0}

default_args = deepcopy(default_option_args)
default_args.update({"user_incar_settings": None,
                     "prev_dir": None,
                     "options": None,
                     "file_transfer_type": None,
                     "uniform_kpt_mode": False,
                     })


test_data = [
    ({}, {}, {}, {}),
    ({"user_incar_settings": {"key": "value"}},
     {"key": "value"},
     {},
     {}),
    ({"options": ["only_even_num_kpts", "True"]},
     {},
     {"only_even_num_kpts": True},
     {}),
    ({"uniform_kpt_mode": True},
     {},
     {"kpt_mode": KpointsMode.uniform},
     {}),
    ({"prev_dir": "a", "file_transfer_type": {"file": "c"}},
     {},
     {},
     {"x": "y"})
]


@pytest.mark.parametrize("modified_settings,"
                         "overridden_incar_settings,"
                         "overridden_options_args,"
                         "prior_info", test_data)
def test_user_incar_settings(mocker,
                             modified_settings,
                             overridden_incar_settings,
                             overridden_options_args,
                             prior_info):
    args = deepcopy(default_args)
    args.update(modified_settings)

    structure = mocker.patch("vise.cli.main_functions.Structure")
    prior_info = mocker.patch("vise.cli.main_functions.PriorInfoFromCalcDir")
    options = mocker.patch("vise.cli.main_functions.CategorizedInputOptions")
    vif = mocker.patch("vise.cli.main_functions.VaspInputFiles")

    prior_info.return_value.input_options_kwargs = prior_info

    name_space = Namespace(**args)
    VaspSet(name_space)

    option_args = deepcopy(default_option_args)
    option_args.update(overridden_options_args)
    option_args.update(prior_info)
    option_args["overridden_potcar"] = {"Mn": "Mn_pv"}
    option_args.pop("poscar")
    option_args["structure"] = structure.from_file.return_value

    options.assert_called_once_with(**option_args)

    incar_settings = defaults.user_incar_settings
    incar_settings.update(overridden_incar_settings)

    vif.assert_called_once_with(options.return_value, incar_settings)


def test_plot_band(tmpdir, test_data_files):
    tmpdir.chdir()  # comment out when one wants to see the figure
    args = Namespace(vasprun_filepath=test_data_files / "KO2_band_vasprun.xml",
                     kpoints_filename=str(test_data_files / "KO2_band_KPOINTS"),
                     y_range=[-10, 10],
                     filename="test.pdf")

    plot_band(args)
