# -*- coding: utf-8 -*-
#  Copyright (c) 2020. Distributed under the terms of the MIT License.

from typing import Optional

from pymatgen.io.vasp.sets import Potcar

from vise.input_set.datasets.dataset_util import PotcarSet
from vise.input_set.xc import Xc
from vise.util.logger import get_logger

logger = get_logger(__name__)


def generate_potcar(symbol_list: list,
                    xc: Xc = Xc.pbe,
                    potcar_set: PotcarSet = PotcarSet.normal,
                    override_potcar_set: Optional[dict] = None):

    potcar_dict = potcar_set.potcar_dict(override_potcar_set)
    potcar_symbols = [potcar_dict[el] for el in symbol_list]
    try:
        return Potcar(potcar_symbols, functional=xc.potcar_functional)
    except IOError as e:
        raise NoPotcarError(e)


class NoPotcarError(Exception):
    pass

