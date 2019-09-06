# -*- coding: utf-8 -*-
from copy import deepcopy
from math import ceil, modf, pow
from typing import Tuple, Union, List

import numpy as np
from obadb.atomate.vasp.config import ST_MATCHER_ANGLE_TOL as ANGLE_TOL
from obadb.atomate.vasp.config import SYMMETRY_TOLERANCE as SYMPREC
from pymatgen import Structure
from pymatgen.io.vasp import Kpoints
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from vise.core.error_classes import InvalidFileError
from vise.database.atom import symbols_to_atom
from vise.database.kpt_centering import kpt_centering
from vise.util.logger import get_logger
from vise.util.structure_handler import structure_to_seekpath, \
    find_spglib_standard_primitive

logger = get_logger(__name__)

__author__ = "Yu Kumagai"
__maintainer__ = "Yu Kumagai"


def make_band_kpoints(kpoints: Kpoints,
                      structure: Structure,
                      num_split_kpoints: int = 1,
                      ref_distance: float = 0.025,
                      time_reversal: bool = True,
                      symprec: float = SYMPREC,
                      angle_tolerance: float = ANGLE_TOL
                      ) -> Union[Tuple[Kpoints, Structure],
                                 Tuple[List[Kpoints], Structure]]:
    """
    Write the KPOINTS file for the band structure calculation.
    Args:
        kpoints (Kpoints):
            Kpoints class object with irreducible k-points with proper weights.
        structure (Structure/IStructure):
        num_split_kpoints (int):
            Number of KPOINTS files used for a band structure calculation.
        ref_distance (float):

        time_reversal (bool):
            Whether time reversal symmetry is considered.
        symprec (float):
        angle_tolerance (float)

    Return:
       (Kpoints, Structure) or ([Kpoints, ..], Structure)
    """

    seekpath_full_info = structure_to_seekpath(structure=structure,
                                               ref_distance=ref_distance,
                                               time_reversal=time_reversal,
                                               symprec=symprec,
                                               angle_tolerance=angle_tolerance)

    # primitive structure
    lattice = seekpath_full_info["primitive_lattice"]
    element_types = seekpath_full_info["primitive_types"]
    species = [symbols_to_atom[i] for i in element_types]
    positions = seekpath_full_info["primitive_positions"]
    primitive = Structure(lattice, species, positions)

    # It would be great if sg is obtained from seekpath.
    # Note: Parameters used for the symmetry search are different between
    #       seekpath and pymatgen.

    sg_analyzer = SpacegroupAnalyzer(structure=primitive, symprec=symprec,
                                     angle_tolerance=angle_tolerance)
    sg = sg_analyzer.get_space_group_number()

    # k-path
    kpath = seekpath_full_info["explicit_kpoints_rel"]
    kpath_label = seekpath_full_info["explicit_kpoints_labels"]
    num_kpoints = ceil(len(kpath) / num_split_kpoints)

    kpoints_list = []
    for x in range(num_split_kpoints):
        k = deepcopy(kpoints)

        k.comment = \
            "Generated by Obadb. Formula: " + \
            primitive.composition.reduced_formula + " SG: " + str(sg)

        divided_kpath = kpath[num_kpoints * x: num_kpoints * (x + 1)]
        divided_kpath_label = \
            kpath_label[num_kpoints * x: num_kpoints * (x + 1)]

        for d, dl in zip(divided_kpath, divided_kpath_label):
            k.num_kpts += 1
            k.kpts.append(d)
            # weight zero is set here.
            k.kpts_weights.append(0)
            k.labels.append(dl)

        kpoints_list.append(k)

    if len(kpoints_list) == 1:
        return kpoints_list[0], primitive
    else:
        return kpoints_list, primitive


def make_kpoints(mode: str,
                 structure: Structure,
                 kpts_density: float,
                 only_even: bool = True,
                 manual_kpts: list = None,
                 num_split_kpoints: int = 1,
                 ref_distance: float = 0.025,
                 kpts_shift: list = None,
                 factor: int = 1,
                 symprec: float = SYMPREC,
                 angle_tolerance: float = ANGLE_TOL,
                 is_magnetization: bool = False
                 ) -> Union[Tuple[Kpoints, Structure, int],
                            Tuple[List[Kpoints], Structure, int]]:
    """Constructs Kpoint object based on default settings depending on the task.

    Note that this function does not check if the primitive cell is standardized
    or not.

    Args:
        mode (str):
            "band":
                Kpoints with the band path will be returned based on the
                seekpath program. The space group is analyzed and primitive
                unitcell that must be used for the band structure calculation is
                returned as well.
            "primitive_uniform":
                Kpoints with uniform k-point sampling. The k-point sampling mesh
                and centering are determined based on the standardized primitive
                unitcell. Structure is also changed if not primitive.
            "manual_set":
                Kpoints with uniform k-point sampling. The k-point sampling mesh
                and centering are determined based on the given lattice. Note
                that only when the angles are 90 degrees, the centering is
                shifted along the perpendicular direction.
                This mode is useful when calculating the supercells.
        structure (Structure/IStructure):
            An input Structure object.
        kpts_density (float):
            Density of k-point mesh along each direction.
        only_even (bool):
            Only even numbered k points are allowed.
        manual_kpts (3x1 list):
            Manual set of the numbers of k-points.
        num_split_kpoints (int):
            "band" requires this variable.
            Number of KPOINTS files used for a band structure calculation.
        ref_distance (float):
        kpts_shift (1x3 list):
            K-point shift in the definition of the vasp setting.
        factor (int):
            Multiplier factor. This is useful for the use of NKRED = factor
            for hybrid xc calculations.
        symprec (float):
            Precision in Angstrom used for the symmetry search.
        angle_tolerance (float):
            Angle tolerance used for symmetry analyzer.
        is_magnetization (bool):
            Whether the magnetization is considered or not.
            This modifies the band structure path for cases w/o inversion.

    Return:
        Tuple of
             Kpoints (Kpoints/list of Kpoints):
             structure (Structure/IStructure):
             sg (int): Space group number
    """
    reciprocal_lattice = structure.lattice.reciprocal_lattice

    comment = f"mode: {mode}"
    sg = None

    # numbers of mesh
    if mode == "primitive_uniform" or mode == "band" or \
            (mode == "manual_set" and manual_kpts is None):
        # check if the primitive is standardized.
        if mode == "primitive_uniform" or mode == "band":
            structure, is_structure_changed = \
                find_spglib_standard_primitive(structure=structure,
                                               symprec=symprec,
                                               angle_tolerance=angle_tolerance)
            if is_structure_changed is True:
                logger.warning(
                    "The input structure is not standardized primitive cell.")

            sg_analyzer = SpacegroupAnalyzer(structure=structure,
                                             symprec=symprec,
                                             angle_tolerance=angle_tolerance)
            sg = sg_analyzer.get_space_group_number()
            sg_symbol = sg_analyzer.get_space_group_symbol()
            logger.info(f"Space group: {sg} {sg_symbol}")

            # Note that the numbers of k-points along all the directions must be
            # the same to keep the crystal symmetry.
            body_centered_orthorhombic = [23, 24, 44, 45, 46, 71, 72, 73, 74]
            body_centered_tetragonal = [79, 80, 81, 82, 87, 88, 97, 98, 107,
                                        108, 109, 110, 119, 120, 121, 122, 139,
                                        140, 141, 142]
            if sg in body_centered_orthorhombic + body_centered_tetragonal:
                average_abc = pow(np.prod(reciprocal_lattice.abc), 1 / 3)
                reciprocal_abc = (average_abc, average_abc, average_abc)
                logger.warning(
                    "To keep the space group symmetry, the number of k-points "
                    "along three directions are kept the same for oI and tI "
                    "Bravais lattice.")
            else:
                reciprocal_abc = reciprocal_lattice.abc
        else:
            reciprocal_abc = reciprocal_lattice.abc

        if only_even:
            kpt_mesh = [int(ceil(kpts_density * r / 2)) * 2 * factor
                        for r in reciprocal_abc]
        else:
            kpt_mesh = [int(ceil(kpts_density * r)) * factor
                        for r in reciprocal_abc]

        comment += f", kpt density: {kpts_density}, factor: {factor}"

    elif manual_kpts:
        kpt_mesh = manual_kpts

    else:
        raise AttributeError(f"Task: {mode} is not supported.\n")

    kpts = (tuple(kpt_mesh),)

    if mode == "band":
        # The structures of mC and oA are differet between spglib and seekpath.
        # see Y. Hinuma et al. Comput. Mater. Sci. 128 (2017) 140–184
        # -- spglib mC
        #  6.048759 -3.479491 0.000000
        #  6.048759  3.479491 0.000000
        # -4.030758  0.000000 6.044512
        # -- seekpath mC
        #  6.048759  3.479491  0.000000
        # -6.048759  3.479491  0.000000
        # -4.030758  0.000000  6.044512
        # -- spglib oA
        #  6.373362  0.000000  0.000000
        #  0.000000  3.200419  5.726024
        #  0.000000 -3.200419  5.726024
        # -- seekpath oA
        #  0.000000  3.200419 -5.726024
        #  0.000000  3.200419  5.726024
        #  6.373362  0.000000  0.000000
        # Therefore, the number of kpts needs to be rotated only for oA.
        a_centered_orthorhombic = (38, 39, 40, 41)
        if sg in a_centered_orthorhombic:
            kpts = ((kpt_mesh[1], kpt_mesh[2], kpt_mesh[0]),)

    # Determine the k-point shift if kpts_shift is not set.
    if kpts_shift is None:
        if mode == "primitive_uniform" or mode == "band":
            kpts_shift = kpt_centering[sg]
            for i in range(3):
                if kpts[0][i] % 2 == 1:
                    kpts_shift[i] = 0
        elif mode == "manual_set":
            kpts_shift = []
            angles = structure.lattice.angles

            for i in range(3):
                # shift kpt mesh center only for the lattice vector being normal
                # to a lattice plane and even number of k-points.
                if abs(angles[i - 2] - 90) < 1e-5 and \
                        abs(angles[i - 1] - 90) < 1e-5 and kpts[0][i] % 2 == 0:
                    kpts_shift.append(0.5)
                else:
                    kpts_shift.append(0.0)

    kpoints = Kpoints(comment=comment, kpts=kpts, kpts_shift=kpts_shift)

    if mode == "band":
        kpts = []
        weights = []
        labels = []
        ir_kpts = irreducible_kpoints(structure=structure,
                                      kpoints=kpoints,
                                      symprec=symprec,
                                      angle_tolerance=angle_tolerance)
        for k in ir_kpts:
            kpts.append(k[0])
            weights.append(k[1])
            labels.append(None)

        kpoints_with_ir_kpt = Kpoints(comment="",
                                      style=Kpoints.supported_modes.Reciprocal,
                                      num_kpts=len(kpts),
                                      kpts=kpts,
                                      kpts_weights=weights,
                                      labels=labels)
        kpoints, structure = \
            make_band_kpoints(kpoints=kpoints_with_ir_kpt,
                              structure=structure,
                              num_split_kpoints=num_split_kpoints,
                              ref_distance=ref_distance,
                              time_reversal=not is_magnetization,
                              symprec=symprec,
                              angle_tolerance=angle_tolerance)

    return kpoints, structure, sg


def get_kpt_dens_from_file(filepath):
    try:
        with open(filepath, "r") as fr:
            lines = fr.readline()
        return float(lines.split()[4].replace(",", ""))

    except:
        raise InvalidFileError(f"failed to read kpt_density from KPOINTS: "
                               f"{filepath}")


def irreducible_kpoints(structure: Structure,
                        kpoints: Kpoints,
                        symprec: float = SYMPREC,
                        angle_tolerance: float = ANGLE_TOL):
    """
    kpoints (Kpoints):
    """
    if kpoints.style == Kpoints.supported_modes.Reciprocal:
        return kpoints.kpts

    if kpoints.style == Kpoints.supported_modes.Monkhorst:
        kpts_shift = [0.5, 0.5, 0.5]
    elif kpoints.style == Kpoints.supported_modes.Gamma:
        kpts_shift = [0.0, 0.0, 0.0]
    else:
        raise ValueError("Other k-points modes are not supported.")

    kpts_shift = [kpts_shift[x] + kpoints.kpts_shift[x] for x in range(3)]
    # modf(x) returns (fraction part, integer part)
    shift = [1 if modf(i)[0] == 0.5 else 0 for i in kpts_shift]

    s = SpacegroupAnalyzer(structure=structure,
                           symprec=symprec,
                           angle_tolerance=angle_tolerance)

    return s.get_ir_reciprocal_mesh(mesh=kpoints.kpts[0], is_shift=shift)


def num_irreducible_kpoints(structure: Structure,
                            kpoints: Kpoints,
                            symprec: float = SYMPREC,
                            angle_tolerance: float = ANGLE_TOL):

    return len(irreducible_kpoints(structure=structure,
                                   kpoints=kpoints,
                                   symprec=symprec,
                                   angle_tolerance=angle_tolerance))



