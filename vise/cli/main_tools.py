# -*- coding: utf-8 -*-
#  Copyright (c) 2020. Distributed under the terms of the MIT License.

from inspect import signature
from pathlib import Path
import re
from typing import Optional, Callable, List, Union, Tuple, Iterable

import yaml

from pymatgen.core.periodic_table import Element

from vise.util.tools import is_str_int, is_str_digit, str2bool
from vise.util.logger import get_logger


logger = get_logger(__name__)


def potcar_str2dict(potcar_list: Union[str, List[str], None]) -> dict:
    """Sanitize potcar names to dict.

    If potcar_dict is None, {} is returned.
    Examples
        ["Mg_pv", O_h"] -> {"Mg": "Mg_pv", "O": "O_h"}
        "Mg_pv" -> {"Mg": "Mg_pv"}
        None -> {}

    Args:
         potcar_list (str/list/None):
            List of Potcar names or a name, including element names before the
            hyphen.

    Returns:
         Dictionary with element names as keys and potcar names as values.
    """
    if potcar_list is None:
        return {}
    elif isinstance(potcar_list, str):
        potcar_list = [potcar_list]

    d = {}
    for p in potcar_list:
        element = p.split("_")[0]
        if element in d:
            raise ValueError("Multiple POTCAR files for an element are not "
                             "supported yet.")
        try:
            Element(element)
        except ValueError:
            raise ValueError(f"First part of POTCAR file name {p} is not an "
                             f"element supported yet.")

        d[element] = p
    return d


def list2dict(flattened_list: Optional[list], key_candidates: Iterable) -> dict:
    """Sanitize a list to a dict with keys in the flags

    If a string in list does not exist in key_candidates, raise ValueError.

    Examples:
        flattened_list = ["ENCUT", "500", "MAGMOM", "4", "4", "LWAVE", "F"]
        key_candidates = ["ENCUT", "MAGMOM", "LWAVE", ...]
        list2dict(flattened_list, key_candidates) =
                            {"ENCUT": 500, "MAGMOM": [4, 4], "LWAVE": False}

        flattened_list = ["ENCUT", "500", "MAGMAM", "4", "4"]
        list2dict(flattened_list, key_candidates) raises ValueError

    Args:
        flattened_list (list):
            Input list.
        key_candidates (list):
            List of key candidates, e.g., INCAR flags.

    Returns:
        Sanitized dict.
    """
    flattened_list = flattened_list or []

    d = {}
    key = None  # key is None at the beginning or after inserting a value.
    value_list = []

    def insert():
        if not value_list:
            raise ValueError(f"Invalid input: {flattened_list}.")
        d[key] = value_list[0] if len(value_list) == 1 else value_list

    for string in flattened_list:
        if key is None and string not in key_candidates:
            raise ValueError(f"Keys are invalid: {flattened_list}.")
        elif string in key_candidates:
            if key:
                insert()
                key = None
                value_list = []
            key = string
        else:
            # We first need to check numbers as 0 and 1 are parse as False and
            # True with str2bool.
            if is_str_int(string):
                value = int(string)
            else:
                try:
                    value = str2bool(string)
                except ValueError:
                    if is_str_digit(string):
                        value = float(string)
                    else:
                        value = string

            value_list.append(value)
    else:
        if key:
            insert()

    return d


# def get_default_args(function: Callable) -> dict:
#     """Get the default values of the arguments in the method/function.

    # inspect._empty means no default.

    # Args:
    #     function (Callable):
    #         Method or function. when class is inserted, cls.__init__ is called.

    # Returns:
    #     Dict of default values.
    # """
    # defaults = {}
    # signature_obj = signature(function)
    # for name, param in signature_obj.parameters.items():
    #     if param.default != _empty:
    #         defaults[name] = param.default

    # return defaults
