"""This module is part of the PeptideBuilder library,
written by Matthew Z. Tien, Dariya K. Sydykova,
Austin G. Meyer, and Claus O. Wilke.

The PeptideBuilder module contains code to generate 3D
structures of peptides. It requires the Geometry module
(also part of the PeptideBuilder library), which contains
default bond lengths and angles for all amino acids.

This module also requires the Bio.PDB module from
Biopython, for structure manipulation.

This file is provided to you under the MIT License."""

import math, warnings
from typing import List, Optional, Union

from Bio.PDB.Polypeptide import is_aa
from Bio.PDB.Atom import Atom
from Bio.PDB.Residue import Residue
from Bio.PDB.Chain import Chain
from Bio.PDB.Model import Model
from Bio.PDB.Structure import Structure
from Bio.PDB.vectors import Vector, rotaxis, calc_dihedral, calc_angle
import numpy as np

from .Geometry import (
    geometry,
    Geo,
    AAGeo,
    AA_AAGeo,
    HfsGeo,
    HssGeo,
    LfsGeo,
    LssGeo,
    LtsGeo,
    LfoGeo,
    LfiGeo,
    AlaGeo,
    Ala_odd_Geo,
    Ala_even_Geo,
    AA_odd_Geo,
    AA_even_Geo,
    LinkerGeo,
    linker_Ala_Geo,
)


def calculateCoordinates(
        refA: Residue, refB: Residue, refC: Residue, L: float, ang: float, di: float
) -> np.ndarray:
    AV = refA.get_vector()
    BV = refB.get_vector()
    CV = refC.get_vector()

    CA = AV - CV
    CB = BV - CV

    ##CA vector
    AX = CA[0]
    AY = CA[1]
    AZ = CA[2]

    ##CB vector
    BX = CB[0]
    BY = CB[1]
    BZ = CB[2]

    ##Plane Parameters
    A = (AY * BZ) - (AZ * BY)
    B = (AZ * BX) - (AX * BZ)
    G = (AX * BY) - (AY * BX)

    ##Dot Product Constant
    F = math.sqrt(BX * BX + BY * BY + BZ * BZ) * L * math.cos(ang * (math.pi / 180.0))

    ##Constants
    const = math.sqrt(
        math.pow((B * BZ - BY * G), 2)
        * (
                -(F * F) * (A * A + B * B + G * G)
                + (
                        B * B * (BX * BX + BZ * BZ)
                        + A * A * (BY * BY + BZ * BZ)
                        - (2 * A * BX * BZ * G)
                        + (BX * BX + BY * BY) * G * G
                        - (2 * B * BY) * (A * BX + BZ * G)
                )
                * L
                * L
        )
    )
    denom = (
            (B * B) * (BX * BX + BZ * BZ)
            + (A * A) * (BY * BY + BZ * BZ)
            - (2 * A * BX * BZ * G)
            + (BX * BX + BY * BY) * (G * G)
            - (2 * B * BY) * (A * BX + BZ * G)
    )

    X = (
                (B * B * BX * F) - (A * B * BY * F) + (F * G) * (-A * BZ + BX * G) + const
        ) / denom

    if (B == 0 or BZ == 0) and (BY == 0 or G == 0):
        const1 = math.sqrt(
            G * G * (-A * A * X * X + (B * B + G * G) * (L - X) * (L + X))
        )
        Y = ((-A * B * X) + const1) / (B * B + G * G)
        Z = -(A * G * G * X + B * const1) / (G * (B * B + G * G))
    else:
        Y = (
                    (A * A * BY * F) * (B * BZ - BY * G)
                    + G * (-F * math.pow(B * BZ - BY * G, 2) + BX * const)
                    - A * (B * B * BX * BZ * F - B * BX * BY * F * G + BZ * const)
            ) / ((B * BZ - BY * G) * denom)
        Z = (
                    (A * A * BZ * F) * (B * BZ - BY * G)
                    + (B * F) * math.pow(B * BZ - BY * G, 2)
                    + (A * BX * F * G) * (-B * BZ + BY * G)
                    - B * BX * const
                    + A * BY * const
            ) / ((B * BZ - BY * G) * denom)

    # Get the new Vector from the origin
    D = Vector(X, Y, Z) + CV
    with warnings.catch_warnings():
        # ignore inconsequential warning
        warnings.simplefilter("ignore")
        temp = calc_dihedral(AV, BV, CV, D) * (180.0 / math.pi)

    di = di - temp
    rot = rotaxis(math.pi * (di / 180.0), CV - BV)
    D = (D - BV).left_multiply(rot) + BV

    return D.get_array()


def makeHfs(segID: int, N, CD1, CG, NB, CA, C, O, geo: HfsGeo) -> Residue:
    ##R-Group
    S_NB_length = geo.S_NB_length
    S_NB_CG_angle = geo.S_NB_CG_angle
    S_NB_CG_CD1_diangle = geo.S_NB_CG_CD1_diangle

    O1_S_length = geo.O1_S_length
    O1_S_NB_angle = geo.O1_S_NB_angle
    O1_S_NB_CG_diangle = geo.O1_S_NB_CG_diangle

    O2_S_length = geo.O2_S_length
    O2_S_NB_angle = geo.O2_S_NB_angle
    O2_S_NB_CA_diangle = geo.O2_S_NB_CA_diangle

    sulfur = calculateCoordinates(
        CD1, CG, NB, S_NB_length, S_NB_CG_angle, S_NB_CG_CD1_diangle
    )
    S = Atom("S", sulfur, 0.0, 1.0, " ", " S", 0, "S")
    oxygen_1 = calculateCoordinates(
        CG, NB, S, O1_S_length, O1_S_NB_angle, O1_S_NB_CG_diangle
    )
    O1 = Atom("O1", oxygen_1, 0.0, 1.0, " ", " O1", 0, "O")
    oxygen_2 = calculateCoordinates(
        CA, NB, S, O2_S_length, O2_S_NB_angle, O2_S_NB_CA_diangle
    )
    O2 = Atom("O2", oxygen_2, 0.0, 1.0, " ", " O2", 0, "O")
    carbon_d2 = calculateCoordinates(
        CG, NB, S, geo.CD2_S_length, geo.CD2_S_NB_angle, geo.CD2_S_NB_CG_diangle
    )
    CD2 = Atom("CD2", carbon_d2, 0.0, 1.0, " ", " CD2", 0, "C")
    carbon_e1 = calculateCoordinates(
        NB, CG, CD1, geo.CE1_CD1_length, geo.CE1_CD1_CG_angle, geo.CE1_CD1_CG_NB_diangle
    )
    CE1 = Atom("CE1", carbon_e1, 0.0, 1.0, " ", " CE1", 0, "C")
    ##Create Residue DS
    res = Residue((" ", segID, " "), "PHE", "    ")
    res.add(N)
    res.add(CD1)
    res.add(CG)
    res.add(NB)
    res.add(CA)
    res.add(C)
    res.add(O)

    res.add(S)
    res.add(O1)
    res.add(O2)
    res.add(CD2)
    res.add(CE1)
    return res


def makeHss(segID: int, N, CD1, CG, NB, CA, C, O, geo: HssGeo) -> Residue:
    S_NB_length = geo.S_NB_length
    S_NB_CG_angle = geo.S_NB_CG_angle
    S_NB_CG_CD1_diangle = geo.S_NB_CG_CD1_diangle

    C1_S_length = geo.C1_S_length
    C1_S_NB_angle = geo.C1_S_NB_angle
    C1_S_NB_CG_diangle = geo.C1_S_NB_CG_diangle

    CZ_C1_length = geo.CZ_C1_length
    CZ_C1_S_angle = geo.CZ_C1_S_angle
    CZ_C1_S_NB_diangle = geo.CZ_C1_S_NB_diangle

    NH_CZ_length = geo.NH_CZ_length
    NH_CZ_C1_angle = geo.NH_CZ_C1_angle
    NH_CZ_C1_S_diangle = geo.NH_CZ_C1_S_diangle

    sulfur = calculateCoordinates(
        CD1, CG, NB, S_NB_length, S_NB_CG_angle, S_NB_CG_CD1_diangle
    )
    S = Atom("S", sulfur, 0.0, 1.0, " ", " S", 0, "S")
    oxygen_1 = calculateCoordinates(
        CA, NB, S, geo.O1_S_length, geo.O1_S_NB_angle, geo.O1_S_NB_CA_diangle
    )
    O1 = Atom("O1", oxygen_1, 0.0, 1.0, " ", " O1", 0, "O")
    oxygen_2 = calculateCoordinates(
        CG, NB, S, geo.O2_S_length, geo.O2_S_NB_angle, geo.O2_S_NB_CG_diangle
    )
    O2 = Atom("O2", oxygen_2, 0.0, 1.0, " ", " O2", 0, "O")
    carbon_1 = calculateCoordinates(
        CG, NB, S, C1_S_length, C1_S_NB_angle, C1_S_NB_CG_diangle
    )
    C1 = Atom("C1", carbon_1, 0.0, 1.0, " ", " C1", 0, "C")
    carbon_z = calculateCoordinates(
        NB, S, C1, CZ_C1_length, CZ_C1_S_angle, CZ_C1_S_NB_diangle
    )
    CZ = Atom("CZ", carbon_z, 0.0, 1.0, " ", " CZ", 0, "C")
    nitrogen_h = calculateCoordinates(
        S, C1, CZ, NH_CZ_length, NH_CZ_C1_angle, NH_CZ_C1_S_diangle
    )
    NH = Atom("NH", nitrogen_h, 0.0, 1.0, " ", " NH", 0, "N")
    carbon_e1 = calculateCoordinates(
        NB, CG, CD1, geo.CE1_CD1_length, geo.CE1_CD1_CG_angle, geo.CE1_CD1_CG_NB_diangle
    )
    CE1 = Atom("CE1", carbon_e1, 0.0, 1.0, " ", " CE1", 0, "C")
    carbon_g2 = calculateCoordinates(
        CG, CD1, CE1, geo.CG2_CE1_lenth, geo.CG2_CE1_CD1_angle, geo.CG2_CE1_CD1_CG_diangle
    )
    CG2 = Atom("CG2", carbon_g2, 0.0, 1.0, " ", " CG2", 0, "C")
    carbon_d2 = calculateCoordinates(
        CD1, CE1, CG2, geo.CD2_CG2_length, geo.CD2_CG2_CE1_angle, geo.CD2_CG2_CE1_CD1_diangle
    )
    CD2 = Atom("CD2", carbon_d2, 0.0, 1.0, " ", " CD2", 0, "C")
    carbon_d3 = calculateCoordinates(
        CD1, CE1, CG2, geo.CD3_CG2_length, geo.CD3_CG2_CE1_angle, geo.CD3_CG2_CE1_CD1_diangle
    )
    CD3 = Atom("CD3", carbon_d3, 0.0, 1.0, " ", " CD3", 0, "C")
    res = Residue((" ", segID, " "), "PHE", "    ")
    res.add(N)
    res.add(CD1)
    res.add(CG)
    res.add(NB)
    res.add(CA)
    res.add(C)
    res.add(O)

    res.add(S)
    res.add(O1)
    res.add(O2)
    res.add(C1)
    res.add(CZ)
    res.add(NH)
    res.add(CE1)
    res.add(CG2)
    res.add(CD3)
    res.add(CD2)

    return res

def makeAa(segID: int, N, CD1, CG, NB, CA, C, O, geo: AAGeo) -> Residue:
    CE1_CD1_length = geo.CE1_CD1_length
    CE1_CD1_CG_angle = geo.CE1_CD1_CG_angle
    CE1_CD1_CG_NB_diangle = geo.CE1_CD1_CG_NB_diangle

    NB_SG_length = geo.NB_SG_length
    CG_NB_SG_angle = geo.CG_NB_SG_angle
    CD1_CG_NB_SG_diangle = geo.CD1_CG_NB_SG_diangle

    OD2_SG_length = geo.OD2_SG_length
    OD2_SG_NB_angle = geo.OD2_SG_NB_angle
    CA_NB_SG_OD2_diangle = geo.CA_NB_SG_OD2_diangle

    OD1_SG_length = geo.OD1_SG_length
    OD1_SG_NB_angle = geo.OD1_SG_NB_angle
    CG_NB_SG_OD1_diangle = geo.CG_NB_SG_OD1_diangle

    SG_CD2_length = geo.SG_CD2_length
    NB_SG_CD2_angle = geo.NB_SG_CD2_angle
    CG_NB_SG_CD2_diangle = geo.CG_NB_SG_CD2_diangle

    CD2_CE2_length = geo.CD2_CE2_length
    SG_CD2_CE2_angle = geo.SG_CD2_CE2_angle
    NB_SG_CD2_CE2_diangle = geo.NB_SG_CD2_CE2_diangle

    CE2_CZ1_length = geo.CE2_CZ1_length
    CD2_CE2_CZ1_angle = geo.CD2_CE2_CZ1_angle
    SG_CD2_CE2_CZ1_diangle = geo.SG_CD2_CE2_CZ1_diangle

    CD2_CE3_length = geo.CD2_CE3_length
    SG_CD2_CE3_angle = geo.SG_CD2_CE3_angle
    NB_SG_CD2_CE3_diangle = geo.NB_SG_CD2_CE3_diangle

    CE3_CZ2_length = geo.CE3_CZ2_length
    CD2_CE3_CZ2_angle = geo.CD2_CE3_CZ2_angle
    SG_CD2_CE3_CZ2_diangle = geo.SG_CD2_CE3_CZ2_diangle

    CZ1_CH_length = geo.CZ1_CH_length
    CE2_CZ1_CH_angle = geo.CE2_CZ1_CH_angle
    CD2_CE2_CZ1_CH_diangle = geo.CD2_CE2_CZ1_CH_diangle

    CH_Cl17_length = geo.CH_Cl17_length
    CZ1_CH_Cl17_angle = geo.CZ1_CH_Cl17_angle
    CE2_CZ1_CH_Cl17_diangle = geo.CE2_CZ1_CH_Cl17_diangle

    carbon_e1 = calculateCoordinates(
        NB, CG, CD1, CE1_CD1_length, CE1_CD1_CG_angle, CE1_CD1_CG_NB_diangle
    )
    CE1 = Atom("CE1", carbon_e1, 0.0, 1.0, " ", " CE1", 0, "C")
    sulfur_g = calculateCoordinates(
        CD1, CG, NB, NB_SG_length, CG_NB_SG_angle, CD1_CG_NB_SG_diangle
    )
    SG = Atom("SG", sulfur_g, 0.0, 1.0, " ", " SG", 0, "S")
    oxygen_d2 = calculateCoordinates(
        CA, NB, SG, OD2_SG_length, OD2_SG_NB_angle, CA_NB_SG_OD2_diangle
    )
    OD2 = Atom("OD2", oxygen_d2, 0.0, 1.0, " ", " OD2", 0, "O")
    oxygen_d1 = calculateCoordinates(
        CG, NB, SG, OD1_SG_length, OD1_SG_NB_angle, CG_NB_SG_OD1_diangle
    )
    OD1 = Atom("OD1", oxygen_d1, 0.0, 1.0, " ", " OD1", 0, "O")

    carbon_d2 = calculateCoordinates(
        CG, NB, SG, SG_CD2_length, NB_SG_CD2_angle, CG_NB_SG_CD2_diangle
    )
    CD2 = Atom("CD2", carbon_d2, 0.0, 1.0, " ", " CD2", 0, "C")
    carbon_e2 = calculateCoordinates(
        NB, SG, CD2, CD2_CE2_length, SG_CD2_CE2_angle, NB_SG_CD2_CE2_diangle
    )
    CE2 = Atom("CE2", carbon_e2, 0.0, 1.0, " ", " CE2", 0, "C")
    carbon_z1 = calculateCoordinates(
        SG, CD2, CE2, CE2_CZ1_length, CD2_CE2_CZ1_angle, SG_CD2_CE2_CZ1_diangle
    )
    CZ1 = Atom("CZ1", carbon_z1, 0.0, 1.0, " ", " CZ1", 0, "C")
    carbon_e3 = calculateCoordinates(
        NB, SG, CD2, CD2_CE3_length, SG_CD2_CE3_angle, NB_SG_CD2_CE3_diangle
    )
    CE3 = Atom("CE3", carbon_e3, 0.0, 1.0, " ", " CE3", 0, "C")
    carbon_z2 = calculateCoordinates(
        SG, CD2, CE3, CE3_CZ2_length, CD2_CE3_CZ2_angle, SG_CD2_CE3_CZ2_diangle
    )
    CZ2 = Atom("CZ2", carbon_z2, 0.0, 1.0, " ", " CZ2", 0, "C")
    carbon_h = calculateCoordinates(
        CD2, CE2, CZ1, CZ1_CH_length, CE2_CZ1_CH_angle, CD2_CE2_CZ1_CH_diangle
    )
    CH = Atom("CH", carbon_h, 0.0, 1.0, " ", " CH", 0, "C")
    chlorine_17 = calculateCoordinates(
        CE2, CZ1, CH, CH_Cl17_length, CZ1_CH_Cl17_angle, CE2_CZ1_CH_Cl17_diangle
    )
    Cl17 = Atom("Cl17", chlorine_17, 0.0, 1.0, " ", " Cl17", 0, "CL")

    res = Residue((" ", segID, " "), "PHE", "    ")
    res.add(N)
    res.add(CD1)
    res.add(CG)
    res.add(NB)
    res.add(CA)
    res.add(C)
    res.add(O)

    res.add(CE1)
    res.add(SG)
    res.add(OD1)
    res.add(OD2)
    res.add(CD2)
    res.add(CE2)
    res.add(CE3)
    res.add(CZ1)
    res.add(CZ2)
    res.add(CH)
    res.add(Cl17)
    return res


def makeAA_AA(segID: int, N, CD1, CG, NB, CA, C, O, geo: AA_AAGeo) -> Residue:
    res = Residue((" ", segID, " "), "PHE", "    ")

    res.add(N)
    res.add(CD1)
    res.add(CG)
    res.add(NB)
    res.add(CA)
    res.add(C)
    res.add(O)
    return res
def makeLfs(segID: int, N, C1, C2, C3, C4, O1, N2, C5, C6, N3, C7, C8, O2, N4, C13, C14, CA, C, O,
                geo: LfsGeo) -> Residue:
    carbon_9 = calculateCoordinates(
        C3, C4, N2, geo.C9_N2_length, geo.C9_N2_C4_angle, geo.C9_N2_C4_C3_diangle
    )
    C9 = Atom("C9", carbon_9, 0.0, 1.0, " ", " C9", 0, "C")

    carbon_10 = calculateCoordinates(
        C4, N2, C9, geo.C10_C9_length, geo.C10_C9_N2_angle, geo.C10_C9_N2_C4_diangle
    )
    C10 = Atom("C10", carbon_10, 0.0, 1.0, " ", " C10", 0, "C")
    carbon_11 = calculateCoordinates(
        N2, C9, C10, geo.C11_C10_length, geo.C11_C10_C9_angle, geo.C11_C10_C9_N2_diangle
    )
    C11 = Atom("C11", carbon_11, 0.0, 1.0, " ", " C11", 0, "C")
    sulfur = calculateCoordinates(
        C5, C6, N3, geo.S_N3_length, geo.S_N3_C6_angle, geo.S_N3_C6_C5_diangle
    )
    S = Atom("S", sulfur, 0.0, 1.0, " ", " S", 0, "S")
    oxygen_4 = calculateCoordinates(
        C7, N3, S, geo.O4_S_length, geo.O4_S_N3_angle, geo.O4_S_N3_C7_diangle
    )
    O4 = Atom("O4", oxygen_4, 0.0, 1.0, " ", " O4", 0, "O")
    oxygen_5 = calculateCoordinates(
        C6, N3, S, geo.O5_S_length, geo.O5_S_N3_angle, geo.O5_S_N3_C6_diangle
    )
    O5 = Atom("O5", oxygen_5, 0.0, 1.0, " ", " O5", 0, "O")
    carbon_12 = calculateCoordinates(
        C6, N3, S, geo.C12_S_length, geo.C12_S_N3_angle, geo.C12_S_N3_C6_diangle
    )
    C12 = Atom("C12", carbon_12, 0.0, 1.0, " ", " C12", 0, "C")
    res = Residue((" ", segID, " "), "SER", "    ")

    res.add(N)
    res.add(C1)
    res.add(C2)
    res.add(C3)
    res.add(C4)
    res.add(O1)
    res.add(N2)
    res.add(C5)
    res.add(C6)
    res.add(N3)
    res.add(C7)
    res.add(C8)
    res.add(O2)
    res.add(N4)
    res.add(C13)
    res.add(C14)
    res.add(CA)
    res.add(C)
    res.add(O)

    res.add(C9)
    res.add(C10)
    res.add(C11)
    res.add(S)
    res.add(O4)
    res.add(O5)
    res.add(C12)
    return res

def makeLss(segID: int, NL, C1, C2, C3, C4, O1, N2, C5, C6, N3, C7, C8, O2, N4, C13, C14, C15, C16, C17, CL, O3,
                geo: LssGeo) -> Residue:
    carbon_9 = calculateCoordinates(
        C3, C4, N2, geo.C9_N2_length, geo.C9_N2_C4_angle, geo.C9_N2_C4_C3_diangle
    )
    C9 = Atom("C9", carbon_9, 0.0, 1.0, " ", " C9", 0, "C")

    carbon_10 = calculateCoordinates(
        C4, N2, C9, geo.C10_C9_length, geo.C10_C9_N2_angle, geo.C10_C9_N2_C4_diangle
    )
    C10 = Atom("C10", carbon_10, 0.0, 1.0, " ", " C10", 0, "C")
    carbon_11 = calculateCoordinates(
        N2, C9, C10, geo.C11_C10_length, geo.C11_C10_C9_angle, geo.C11_C10_C9_N2_diangle
    )
    C11 = Atom("C11", carbon_11, 0.0, 1.0, " ", " C11", 0, "C")
    sulfur = calculateCoordinates(
        C5, C6, N3, geo.S_N3_length, geo.S_N3_C6_angle, geo.S_N3_C6_C5_diangle
    )
    S = Atom("S", sulfur, 0.0, 1.0, " ", " S", 0, "S")
    oxygen_4 = calculateCoordinates(
        C7, N3, S, geo.O4_S_length, geo.O4_S_N3_angle, geo.O4_S_N3_C7_diangle
    )
    O4 = Atom("O4", oxygen_4, 0.0, 1.0, " ", " O4", 0, "O")
    oxygen_5 = calculateCoordinates(
        C6, N3, S, geo.O5_S_length, geo.O5_S_N3_angle, geo.O5_S_N3_C6_diangle
    )
    O5 = Atom("O5", oxygen_5, 0.0, 1.0, " ", " O5", 0, "O")
    carbon_12 = calculateCoordinates(
        C6, N3, S, geo.C12_S_length, geo.C12_S_N3_angle, geo.C12_S_N3_C6_diangle
    )
    C12 = Atom("C12", carbon_12, 0.0, 1.0, " ", " C12", 0, "C")

    res = Residue((" ", segID, " "), "SER", "    ")
    res.add(NL)
    res.add(C1)
    res.add(C2)
    res.add(C3)
    res.add(C4)
    res.add(O1)
    res.add(N2)
    res.add(C5)
    res.add(C6)
    res.add(N3)
    res.add(C7)
    res.add(C8)
    res.add(O2)
    res.add(N4)
    res.add(C13)
    res.add(C14)
    res.add(C15)
    res.add(C16)
    res.add(C17)
    res.add(CL)
    res.add(O3)

    res.add(C9)
    res.add(C10)
    res.add(C11)
    res.add(S)
    res.add(O4)
    res.add(O5)
    res.add(C12)
    return res

def makeAla(segID: int, N, CA, C, O, geo: AlaGeo) -> Residue:
    """Creates an Alanine residue"""
    ##R-Group

    carbon_b = calculateCoordinates(
        N, C, CA, geo.CB_CA_length, geo.CB_CA_C_angle, geo.CB_CA_C_N_diangle
    )
    CB = Atom("CB", carbon_b, 0.0, 1.0, " ", " CB", 0, "C")

    res = Residue((" ", segID, " "), "ALA", "    ")
    res.add(N)
    res.add(CA)
    res.add(C)
    res.add(O)
    res.add(CB)
    return res
def make_odd_Aa(segID: int, N, CD1, CG, NB, CA, C, O, geo: AA_odd_Geo) -> Residue:
    carbon_e1 = calculateCoordinates(
        NB, CG, CD1, geo.CE1_CD1_length, geo.CE1_CD1_CG_angle, geo.CE1_CD1_CG_NB_diangle
    )
    CE1 = Atom("CE1", carbon_e1, 0.0, 1.0, " ", " CE1", 0, "C")
    sulfur_g = calculateCoordinates(
        CD1, CG, NB, geo.SG_NB_length, geo.SG_NB_CG_angle, geo.SG_NB_CG_CD1_diangle
    )
    SG = Atom("SG", sulfur_g, 0.0, 1.0, " ", " SG", 0, "S")
    oxygen_d2 = calculateCoordinates(
        CA, NB, SG, geo.OD2_SG_length, geo.OD2_SG_NB_angle, geo.OD2_SG_NB_CA_diangle
    )
    OD2 = Atom("OD2", oxygen_d2, 0.0, 1.0, " ", " OD2", 0, "O")
    oxygen_d1 = calculateCoordinates(
        CG, NB, SG, geo.OD1_SG_length, geo.OD1_SG_NB_angle, geo.OD1_SG_NB_CG_diangle
    )
    OD1 = Atom("OD1", oxygen_d1, 0.0, 1.0, " ", " OD1", 0, "O")

    carbon_d2 = calculateCoordinates(
        CG, NB, SG, geo.CD2_SG_length, geo.CD2_SG_NB_angle, geo.CD2_SG_NB_CG_angle
    )
    CD2 = Atom("CD2", carbon_d2, 0.0, 1.0, " ", " CD2", 0, "C")
    carbon_e2 = calculateCoordinates(
        NB, SG, CD2, geo.CE2_CD2_length, geo.CE2_CD2_SG_angle, geo.CE2_CD2_SG_NB_diangle
    )
    CE2 = Atom("CE2", carbon_e2, 0.0, 1.0, " ", " CE2", 0, "C")
    carbon_z1 = calculateCoordinates(
        SG, CD2, CE2, geo.CZ1_CE2_length, geo.CZ1_CE2_CD2_angle, geo.CZ1_CE2_CD2_SG_diangle
    )
    CZ1 = Atom("CZ1", carbon_z1, 0.0, 1.0, " ", " CZ1", 0, "C")
    carbon_e3 = calculateCoordinates(
        NB, SG, CD2, geo.CE3_CD2_length, geo.CE3_CD2_SG_angle, geo.CE3_CD2_SG_NB_diangle
    )
    CE3 = Atom("CE3", carbon_e3, 0.0, 1.0, " ", " CE3", 0, "C")
    carbon_z2 = calculateCoordinates(
        SG, CD2, CE3, geo.CZ2_CE3_length, geo.CZ2_CE3_CD2_angle, geo.CZ2_CE3_CD2_SG_diangle
    )
    CZ2 = Atom("CZ2", carbon_z2, 0.0, 1.0, " ", " CZ2", 0, "C")
    carbon_h = calculateCoordinates(
        CD2, CE2, CZ1, geo.CH_CZ1_length, geo.CH_CZ1_CE2_angle, geo.CH_CZ1_CE2_CD2_diangle
    )
    CH = Atom("CH", carbon_h, 0.0, 1.0, " ", " CH", 0, "C")
    chlorine_17 = calculateCoordinates(
        CE2, CZ1, CH, geo.Cl17_CH_length, geo.Cl17_CH_CZ1_angle, geo.Cl17_CH_CZ1_CE2_diangle
    )
    Cl17 = Atom("Cl17", chlorine_17, 0.0, 1.0, " ", " Cl17", 0, "CL")
    res = Residue((" ", segID, " "), "PHE", "    ")
    res.add(N)
    res.add(CD1)
    res.add(CG)
    res.add(NB)
    res.add(CA)
    res.add(C)
    res.add(O)

    res.add(CE1)
    res.add(SG)
    res.add(OD1)
    res.add(OD2)
    res.add(CD2)
    res.add(CE2)
    res.add(CE3)
    res.add(CZ1)
    res.add(CZ2)
    res.add(CH)
    res.add(Cl17)
    return res
def make_even_Aa(segID: int, N, CD1, CG, NB, CA, C, O, geo: AA_even_Geo) -> Residue:
    carbon_e1 = calculateCoordinates(
        NB, CG, CD1, geo.CE1_CD1_length, geo.CE1_CD1_CG_angle, geo.CE1_CD1_CG_NB_diangle
    )
    CE1 = Atom("CE1", carbon_e1, 0.0, 1.0, " ", " CE1", 0, "C")
    sulfur_g = calculateCoordinates(
        CD1, CG, NB, geo.SG_NB_length, geo.SG_NB_CG_angle, geo.SG_NB_CG_CD1_diangle
    )
    SG = Atom("SG", sulfur_g, 0.0, 1.0, " ", " SG", 0, "S")
    oxygen_d2 = calculateCoordinates(
        CA, NB, SG, geo.OD2_SG_length, geo.OD2_SG_NB_angle, geo.OD2_SG_NB_CA_diangle
    )
    OD2 = Atom("OD2", oxygen_d2, 0.0, 1.0, " ", " OD2", 0, "O")
    oxygen_d1 = calculateCoordinates(
        CG, NB, SG, geo.OD1_SG_length, geo.OD1_SG_NB_angle, geo.OD1_SG_NB_CG_diangle
    )
    OD1 = Atom("OD1", oxygen_d1, 0.0, 1.0, " ", " OD1", 0, "O")

    carbon_d2 = calculateCoordinates(
        CG, NB, SG, geo.CD2_SG_length, geo.CD2_SG_NB_angle, geo.CD2_SG_NB_CG_angle
    )
    CD2 = Atom("CD2", carbon_d2, 0.0, 1.0, " ", " CD2", 0, "C")
    carbon_e2 = calculateCoordinates(
        NB, SG, CD2, geo.CE2_CD2_length, geo.CE2_CD2_SG_angle, geo.CE2_CD2_SG_NB_diangle
    )
    CE2 = Atom("CE2", carbon_e2, 0.0, 1.0, " ", " CE2", 0, "C")
    carbon_z1 = calculateCoordinates(
        SG, CD2, CE2, geo.CZ1_CE2_length, geo.CZ1_CE2_CD2_angle, geo.CZ1_CE2_CD2_SG_diangle
    )
    CZ1 = Atom("CZ1", carbon_z1, 0.0, 1.0, " ", " CZ1", 0, "C")
    carbon_e3 = calculateCoordinates(
        NB, SG, CD2, geo.CE3_CD2_length, geo.CE3_CD2_SG_angle, geo.CE3_CD2_SG_NB_diangle
    )
    CE3 = Atom("CE3", carbon_e3, 0.0, 1.0, " ", " CE3", 0, "C")
    carbon_z2 = calculateCoordinates(
        SG, CD2, CE3, geo.CZ2_CE3_length, geo.CZ2_CE3_CD2_angle, geo.CZ2_CE3_CD2_SG_diangle
    )
    CZ2 = Atom("CZ2", carbon_z2, 0.0, 1.0, " ", " CZ2", 0, "C")
    carbon_h = calculateCoordinates(
        CD2, CE2, CZ1, geo.CH_CZ1_length, geo.CH_CZ1_CE2_angle, geo.CH_CZ1_CE2_CD2_diangle
    )
    CH = Atom("CH", carbon_h, 0.0, 1.0, " ", " CH", 0, "C")
    chlorine_17 = calculateCoordinates(
        CE2, CZ1, CH, geo.Cl17_CH_length, geo.Cl17_CH_CZ1_angle, geo.Cl17_CH_CZ1_CE2_diangle
    )
    Cl17 = Atom("Cl17", chlorine_17, 0.0, 1.0, " ", " Cl17", 0, "CL")
    res = Residue((" ", segID, " "), "PHE", "    ")
    res.add(N)
    res.add(CD1)
    res.add(CG)
    res.add(NB)
    res.add(CA)
    res.add(C)
    res.add(O)

    res.add(CE1)
    res.add(SG)
    res.add(OD1)
    res.add(OD2)
    res.add(CD2)
    res.add(CE2)
    res.add(CE3)
    res.add(CZ1)
    res.add(CZ2)
    res.add(CH)
    res.add(Cl17)
    return res
def make_odd_Ala(segID: int, N, CA, C, O, geo: Ala_odd_Geo) -> Residue:
    """Creates an Alanine residue"""
    ##R-Group

    carbon_b = calculateCoordinates(
        N, C, CA, geo.CB_CA_length, geo.CB_CA_C_angle, geo.CB_CA_C_N_diangle
    )
    CB = Atom("CB", carbon_b, 0.0, 1.0, " ", " CB", 0, "C")

    res = Residue((" ", segID, " "), "ALA", "    ")
    res.add(N)
    res.add(CA)
    res.add(C)
    res.add(O)
    res.add(CB)
    return res
def make_even_Ala(segID: int, N, CA, C, O, geo: Ala_even_Geo) -> Residue:
    """Creates an Alanine residue"""
    ##R-Group

    carbon_b = calculateCoordinates(
        N, C, CA, geo.CB_CA_length, geo.CB_CA_C_angle, geo.CB_CA_C_N_diangle
    )
    CB = Atom("CB", carbon_b, 0.0, 1.0, " ", " CB", 0, "C")

    res = Residue((" ", segID, " "), "ALA", "    ")
    res.add(N)
    res.add(CA)
    res.add(C)
    res.add(O)
    res.add(CB)
    return res
def makeLinker(segID: int, N1, C5, C6 ,C7, C8, O3, N2, C9, C10, O4, N3, C11, C12, C13, C4, O2, geo: LinkerGeo) -> Residue:
    res = Residue((" ", segID, " "), "GLY", "    ")
    res.add(N1)
    res.add(C5)
    res.add(C6)
    res.add(C7)
    res.add(C8)
    res.add(O3)
    res.add(N2)
    res.add(C9)
    res.add(C10)
    res.add(O4)
    res.add(N3)
    res.add(C11)
    res.add(C12)
    res.add(C13)
    res.add(C4)
    res.add(O2)
    return res
def make_linker_Ala(segID: int, N, CA, C, O, geo: linker_Ala_Geo) -> Residue:
    """Creates an Alanine residue"""
    ##R-Group

    carbon_b = calculateCoordinates(
        N, C, CA, geo.CB_CA_length, geo.CB_CA_C_angle, geo.CB_CA_C_N_diangle
    )
    CB = Atom("CB", carbon_b, 0.0, 1.0, " ", " CB", 0, "C")

    res = Residue((" ", segID, " "), "ALA", "    ")
    res.add(N)
    res.add(CA)
    res.add(C)
    res.add(O)
    res.add(CB)
    return res
def make_res_of_type_natural(segID: int, N, CA, C, O, geo: Geo) -> Residue:
    if isinstance(geo, AlaGeo):
        res = makeAla(segID, N, CA, C, O, geo)
    elif isinstance(geo, Ala_odd_Geo):
        res = make_odd_Ala(segID, N, CA, C, O, geo)
    elif isinstance(geo, Ala_even_Geo):
        res = make_even_Ala(segID, N, CA, C, O, geo)
    elif isinstance(geo, linker_Ala_Geo):
        res = make_linker_Ala(segID, N, CA, C, O, geo)
    return res

def make_res_of_type_linker(segID: int, N1, C5, C6 ,C7, C8, O3, N2, C9, C10, O4, N3, C11, C12, C13, C4, O2,
                            geo: Geo) -> Residue:
    if isinstance(geo, LinkerGeo):
        res = makeLinker(segID, N1, C5, C6, C7, C8, O3, N2, C9, C10, O4, N3, C11, C12, C13, C4, O2, geo)
    return res
def make_res_of_type_aa(segID: int, N, CD1, CG, NB, CA, C, O, geo: Geo, ) -> Residue:
    if isinstance(geo, AAGeo):
        res = makeAa(segID, N, CD1, CG, NB, CA, C, O, geo)
    elif isinstance(geo, AA_AAGeo):
        res = makeAA_AA(segID, N, CD1, CG, NB, CA, C, O, geo)
    elif isinstance(geo, HfsGeo):
        res = makeHfs(segID, N, CD1, CG, NB, CA, C, O, geo)
    elif isinstance(geo, HssGeo):
        res = makeHss(segID, N, CD1, CG, NB, CA, C, O, geo)
    elif isinstance(geo, AA_odd_Geo):
        res = make_odd_Aa(segID, N, CD1, CG, NB, CA, C, O, geo)
    elif isinstance(geo, AA_even_Geo):
        res = make_even_Aa(segID, N, CD1, CG, NB, CA, C, O, geo)
    return res


def make_res_of_type_linker2_1(segID: int, N, C1, C2, C3, C4, O1, N2, C5, C6, N3, C7, C8, O2, N4, C13, C14, CA,
                               C, O, geo: Geo, ) -> Residue:
    if isinstance(geo, LfsGeo):
        res = makeLfs(segID, N, C1, C2, C3, C4, O1, N2, C5, C6, N3, C7, C8, O2, N4, C13, C14, CA, C, O, geo)
    return res
def make_res_of_type_linker2_3(segID: int, NL, C1, C2, C3, C4, O1, N2, C5, C6, N3, C7, C8, O2, N4, C13, C14,
                               C15, C16, C17, CL,O3,geo: Geo, ) -> Residue:
    if isinstance(geo, LssGeo):
        res = makeLss(segID, NL, C1, C2, C3, C4, O1, N2, C5, C6, N3, C7, C8, O2, N4, C13, C14, C15, C16, C17,
                          CL, O3,geo)
        return res
def initialize_res_natural(residue: Union[Geo, str]) -> Structure:
    """Creates a new structure containing a single amino acid. The type and
    geometry of the amino acid are determined by the argument, which has to be
    either a geometry object or a single-letter amino acid code.
    The amino acid will be placed into chain A of model 0."""

    if isinstance(residue, Geo):
        geo = residue
    elif isinstance(residue, str):
        geo = geometry(residue)
    else:
        raise ValueError("Invalid residue argument:", residue)

    segID = 1
    AA = geo.residue_name
    CA_N_length = geo.CA_N_length
    CA_C_length = geo.CA_C_length
    N_CA_C_angle = geo.N_CA_C_angle

    CA_coord = np.array([0.0, 0.0, 0.0])
    C_coord = np.array([CA_C_length, 0, 0])
    N_coord = np.array(
        [
            CA_N_length * math.cos(N_CA_C_angle * (math.pi / 180.0)),
            CA_N_length * math.sin(N_CA_C_angle * (math.pi / 180.0)),
            0,
        ]
    )

    N = Atom("N", N_coord, 0.0, 1.0, " ", " N", 0, "N")
    CA = Atom("CA", CA_coord, 0.0, 1.0, " ", " CA", 0, "C")
    C = Atom("C", C_coord, 0.0, 1.0, " ", " C", 0, "C")

    ##Create Carbonyl atom (to be moved later)
    C_O_length = geo.C_O_length
    CA_C_O_angle = geo.CA_C_O_angle
    N_CA_C_O_diangle = geo.N_CA_C_O_diangle

    carbonyl = calculateCoordinates(
        N, CA, C, C_O_length, CA_C_O_angle, N_CA_C_O_diangle
    )
    O = Atom("O", carbonyl, 0.0, 1.0, " ", " O", 0, "O")

    res = make_res_of_type_natural(segID, N, CA, C, O, geo)

    cha = Chain("A")
    cha.add(res)

    mod = Model(0)
    mod.add(cha)

    struc = Structure("X")
    struc.add(mod)
    return struc
def initialize_res(residue: Union[Geo, str]) -> Structure:
    """Creates a new structure containing a single amino acid. The type and
    geometry of the amino acid are determined by the argument, which has to be
    either a geometry object or a single-letter amino acid code.
    The amino acid will be placed into cxxhain A of model 0."""

    if isinstance(residue, Geo):
        geo = residue
    elif isinstance(residue, str):
        geo = geometry(residue)
    else:
        raise ValueError("Invalid residue argument:", residue)

    segID = 1
    AA = geo.residue_name
    N_CD1_length = geo.N_CD1_length
    CD1_CG_length = geo.CD1_CG_length
    N_CD1_CG_angle = geo.N_CD1_CG_angle

    CD1_coord = np.array([0.0, 0.0, 0.0])
    CG_coord = np.array([CD1_CG_length, 0, 0])
    N_coord = np.array(
        [
            N_CD1_length * math.cos(N_CD1_CG_angle * (math.pi / 180.0)),
            N_CD1_length * math.sin(N_CD1_CG_angle * (math.pi / 180.0)),
            0,
        ]
    )

    N = Atom("N", N_coord, 0.0, 1.0, " ", " N", 0, "N")
    CG = Atom("CG", CG_coord, 0.0, 1.0, " ", " CG", 0, "C")
    CD1 = Atom("CD1", CD1_coord, 0.0, 1.0, " ", " CD1", 0, "C")

    N_CD1_CG_NB_diangle = geo.N_CD1_CG_NB_diangle

    CG_NB_length = geo.CG_NB_length
    CG_NB_CA_angle = geo.CG_NB_CA_angle
    CG_NB_CA_C_diangle = geo.CG_NB_CA_C_diangle

    CA_NB_length = geo.CA_NB_length
    CA_C_length = geo.CA_C_length
    NB_CA_C_angle = geo.NB_CA_C_angle
    CD1_CG_NB_angle = geo.CD1_CG_NB_angle
    CD1_CG_NB_CA_diangle = geo.CD1_CG_NB_CA_diangle

    NB = calculateCoordinates(
        N, CD1, CG, CG_NB_length, CD1_CG_NB_angle, N_CD1_CG_NB_diangle
    )
    NB = Atom("NB", NB, 0.0, 1.0, " ", " NB", 0, "N")
    carbon_a = calculateCoordinates(
        CD1, CG, NB, CA_NB_length, CG_NB_CA_angle, CD1_CG_NB_CA_diangle
    )
    CA = Atom("CA", carbon_a, 0.0, 1.0, " ", " CA", 0, "C")
    carbon = calculateCoordinates(
        CG, NB, CA, CA_C_length, NB_CA_C_angle, CG_NB_CA_C_diangle
    )
    C = Atom("C", carbon, 0.0, 1.0, " ", " C", 0, "C")

    ##Create Carbonyl atom (to be moved later)
    C_O_length = geo.C_O_length
    CA_C_O_angle = geo.CA_C_O_angle
    NB_CA_C_O_diangle = geo.NB_CA_C_O_diangle1

    carbonyl = calculateCoordinates(
        NB, CA, C, C_O_length, CA_C_O_angle, NB_CA_C_O_diangle
    )
    O = Atom("O", carbonyl, 0.0, 1.0, " ", " O", 0, "O")

    res = make_res_of_type_aa(segID, N, CD1, CG, NB, CA, C, O, geo)

    cha = Chain("A")
    cha.add(res)

    mod = Model(0)
    mod.add(cha)

    struc = Structure("X")
    struc.add(mod)
    return struc


def getReferenceResidue(structure: Structure) -> Residue:
    """Returns the last residue of chain A model 0 of the given structure.

    This function is a helper function that should not normally be called
    directly."""

    # If the following line doesn't work we're in trouble.
    # Likely initialize_res() wasn't called.
    resRef = structure[0]["A"].child_list[-1]

    # If the residue is not an amino acid we're in trouble.
    # Likely somebody is trying to append residues to an existing
    # structure that has non-amino-acid molecules in the chain.
    assert is_aa(resRef)

    return resRef

def add_residue_from_geo_ala_aa(structure: Structure, geo: Geo) -> Structure:

    resRef = getReferenceResidue(structure)
    AA = geo.residue_name
    segID = resRef.get_id()[1]
    segID += 1


    N_coord = calculateCoordinates(
        resRef["N"], resRef["CA"], resRef["C"], geo.N_C_length, geo.N_C_CA_angle, geo.N_C_CA_N_diangle
    )
    N = Atom("N", N_coord, 0.0, 1.0, " ", " N", 0, "N")

    CD1_coord = calculateCoordinates(
        resRef["CA"], resRef["C"], N, geo.CD1_N_length, geo.CD1_N_C_angle, geo.CD1_N_C_CA_diangle
    )
    CD1 = Atom("CD1", CD1_coord, 0.0, 1.0, " ", " CD1", 0, "C")

    CG_coord = calculateCoordinates(resRef["C"], N, CD1, geo.CG_CD1_length, geo.CG_CD1_N_angle,
                                    geo.CG_CD1_N_C_diangle)
    CG = Atom("CG", CG_coord, 0.0, 1.0, " ", " CG", 0, "C")

    NB = calculateCoordinates(
        N, CD1, CG, geo.NB_CG_length, geo.NB_CG_CD1_angle, geo.NB_CG_CD1_N_diangle
    )
    NB = Atom("NB", NB, 0.0, 1.0, " ", " NB", 0, "N")
    carbon_a = calculateCoordinates(
        CD1, CG, NB, geo.CA_NB_length, geo.CA_NB_CG_angle, geo.CA_NB_CG_CD1_diangle
    )
    CA = Atom("CA", carbon_a, 0.0, 1.0, " ", " CA", 0, "C")
    carbon = calculateCoordinates(
        CG, NB, CA, geo.C_CA_length, geo.C_CA_NB_angle, geo.C_CA_NB_CG_diangle
    )
    C = Atom("C", carbon, 0.0, 1.0, " ", " C", 0, "C")
    ##Create Carbonyl atom (to be moved later)

    carbonyl = calculateCoordinates(
        NB, CA, C, geo.O_C_length, geo.O_C_CA_angle, geo.O_C_CA_NB_diangle
    )
    O = Atom("O", carbonyl, 0.0, 1.0, " ", " O", 0, "O")

    res = make_res_of_type_aa(segID, N, CD1, CG, NB, CA, C, O, geo)


    structure[0]["A"].add(res)
    return structure

def add_residue_ala_aa(structure: Structure, residue: Union[Geo, str], phi=-120, psi_im1=140, omega=-370
) -> Structure:

    if isinstance(residue, Geo):
        geo = residue
    elif isinstance(residue, str):
        geo = geometry(residue)
        geo.phi = phi
        geo.psi_im1 = psi_im1
        if omega > -361:
            geo.omega = omega
    else:
        raise ValueError("Invalid residue argument:", residue)

    return add_residue_from_geo_ala_aa(structure, geo)

def add_residue_from_geo_aa_ala(structure: Structure, geo: Geo) -> Structure:
    """Adds a residue to chain A model 0 of the given structure, and
    returns the new structure. The residue to be added is determined by
    the geometry object given as second argument.

    This function is a helper function and should not normally be called
    directly. Call add_residue() instead."""
    resRef = getReferenceResidue(structure)
    AA = geo.residue_name
    segID = resRef.get_id()[1]
    segID += 1

    ##geometry to bring together residue


    N_coord = calculateCoordinates(
        resRef["NB"], resRef["CA"], resRef["C"], geo.N_C_length, geo.N_C_CA_angle, geo.N_C_CA_NB_diangle
    )
    N = Atom("N", N_coord, 0.0, 1.0, " ", " N", 0, "N")

    CA_coord = calculateCoordinates(
        resRef["CA"], resRef["C"], N, geo.CA_N_length, geo.CA_N_C_angle, geo.CA_N_C_CA_diangle
    )
    CA = Atom("CA", CA_coord, 0.0, 1.0, " ", " CA", 0, "C")

    C_coord = calculateCoordinates(resRef["C"], N, CA, geo.C_CA_length, geo.C_CA_N_angle, geo.C_CA_N_C_diangle)
    C = Atom("C", C_coord, 0.0, 1.0, " ", " C", 0, "C")

    ##Create Carbonyl atom (to be moved later)

    carbonyl = calculateCoordinates(
        N, CA, C, geo.C_O_length, geo.CA_C_O_angle, geo.N_CA_C_O_diangle
    )
    O = Atom("O", carbonyl, 0.0, 1.0, " ", " O", 0, "O")

    res = make_res_of_type_natural(segID, N, CA, C, O, geo)


    structure[0]["A"].add(res)
    return structure

def add_residue_aa_ala(
        structure: Structure, residue: Union[Geo, str], phi=-120, psi_im1=140, omega=-370
) -> Structure:


    if isinstance(residue, Geo):
        geo = residue
    elif isinstance(residue, str):
        geo = geometry(residue)
        geo.phi = phi
        geo.psi_im1 = psi_im1
        if omega > -361:
            geo.omega = omega
    else:
        raise ValueError("Invalid residue argument:", residue)

    return add_residue_from_geo_aa_ala(structure, geo)


def add_residue_from_geo_alalinker(structure: Structure, geo: Geo) -> Structure:
    """Adds a residue to chain A model 0 of the given structure, and
    returns the new structure. The residue to be added is determined by
    the geometry object given as second argument.

    This function is a helper function and should not normally be called
    directly. Call add_residue() instead."""
    resRef = getReferenceResidue(structure)
    AA = geo.residue_name
    segID = resRef.get_id()[1]
    segID += 1

    N1_C_length=geo.N1_C_length
    N1_C_CA_angle=geo.N1_C_CA_angle
    N1_C_CA_N_diangle=geo.N1_C_CA_N_diangle

    C5_N1_length=geo.C5_N1_length
    C5_N1_C_angle=geo.C5_N1_C_angle
    C5_N1_C_CA_diangle=geo.C5_N1_C_CA_diangle

    C6_C5_length=geo.C6_C5_length
    C6_C5_N1_angle=geo.C6_C5_N1_angle
    C6_C5_N1_C_diangle=geo.C6_C5_N1_C_diangle

    C7_C6_length=geo.C7_C6_length
    C7_C6_C5_angle=geo.C7_C6_C5_angle
    C7_C6_C5_N1_diangle=geo.C7_C6_C5_N1_diangle

    C8_C7_length=geo.C8_C7_length
    C8_C7_C6_angle=geo.C8_C7_C6_angle
    C8_C7_C6_C5_diangle=geo.C8_C7_C6_C5_diangle

    O3_C8_length=geo.O3_C8_length
    O3_C8_C7_angle=geo.O3_C8_C7_angle
    O3_C8_C7_C6_diangle=geo.O3_C8_C7_C6_diangle

    N2_C8_length=geo.N2_C8_length
    N2_C8_C7_angle=geo.N2_C8_C7_angle
    N2_C8_C7_C6_diangle=geo.N2_C8_C7_C6_diangle

    C9_N2_length=geo.C9_N2_length
    C9_N2_C8_angle=geo.C9_N2_C8_angle
    C9_N2_C8_C7_diangle=geo.C9_N2_C8_C7_diangle

    C10_C9_length=geo.C10_C9_length
    C10_C9_N2_angle=geo.C10_C9_N2_angle
    C10_C9_N2_C8_diangle=geo.C10_C9_N2_C8_diangle

    O4_C10_length=geo.O4_C10_length
    O4_C10_C9_angle=geo.O4_C10_C9_angle
    O4_C10_C9_N2_diangle=geo.O4_C10_C9_N2_diangle

    N3_C10_length=geo.N3_C10_length
    N3_C10_C9_angle=geo.N3_C10_C9_angle
    N3_C10_C9_N2_diangle=geo.N3_C10_C9_N2_diangle

    C11_N3_length=geo.C11_N3_length
    C11_N3_C10_angle=geo.C11_N3_C10_angle
    C11_N3_C10_C9_diangle=geo.C11_N3_C10_C9_diangle

    C12_C11_length=geo.C12_C11_length
    C12_C11_N3_angle=geo.C12_C11_N3_angle
    C12_C11_N3_C10_diangle=geo.C12_C11_N3_C10_diangle

    C13_C12_length=geo.C13_C12_length
    C13_C12_C11_angle=geo.C13_C12_C11_angle
    C13_C12_C11_N3_diangle=geo.C13_C12_C11_N3_diangle

    N1_coord = calculateCoordinates(
        resRef["N"], resRef["CA"], resRef["C"], N1_C_length, N1_C_CA_angle, N1_C_CA_N_diangle
    )
    N1 = Atom("N", N1_coord, 0.0, 1.0, " ", " N", 0, "N")
    C5_coord = calculateCoordinates(
        resRef["CA"], resRef["C"], N1, C5_N1_length, C5_N1_C_angle, C5_N1_C_CA_diangle
    )
    C5 = Atom("CA", C5_coord, 0.0, 1.0, " ", " CG", 0, "C")
    C6_coord = calculateCoordinates(resRef["C"], N1, C5, C6_C5_length, C6_C5_N1_angle, C6_C5_N1_C_diangle)
    C6 = Atom("CB", C6_coord, 0.0, 1.0, " ", " CB", 0, "C")

    C7_coord = calculateCoordinates(N1, C5, C6,C7_C6_length, C7_C6_C5_angle, C7_C6_C5_N1_diangle)
    C7 = Atom("CG", C7_coord, 0.0, 1.0, " ", " CA", 0, "C")
    C8_coord = calculateCoordinates(C5, C6, C7, C8_C7_length, C8_C7_C6_angle, C8_C7_C6_C5_diangle)
    C8 = Atom("C", C8_coord, 0.0, 1.0, " ", " C", 0, "C")
    O3_coord = calculateCoordinates(C6, C7, C8, O3_C8_length, O3_C8_C7_angle, O3_C8_C7_C6_diangle)
    O3 = Atom("O", O3_coord, 0.0, 1.0, " ", " O", 0, "O")
    N2_coord = calculateCoordinates(C6, C7, C8, N2_C8_length, N2_C8_C7_angle, N2_C8_C7_C6_diangle)
    N2 = Atom("N2", N2_coord, 0.0, 1.0, " ", " N", 0, "N")
    C9_coord = calculateCoordinates(C7, C8, N2, C9_N2_length, C9_N2_C8_angle, C9_N2_C8_C7_diangle)
    C9 = Atom("C9", C9_coord, 0.0, 1.0, " ", " CA", 0, "C")
    C10_coord = calculateCoordinates(C8, N2, C9,C10_C9_length, C10_C9_N2_angle, C10_C9_N2_C8_diangle)
    C10 = Atom("C10", C10_coord, 0.0, 1.0, " ", " C", 0, "C")
    O4_coord = calculateCoordinates(N2, C9, C10, O4_C10_length, O4_C10_C9_angle, O4_C10_C9_N2_diangle)
    O4 = Atom("O4", O4_coord, 0.0, 1.0, " ", " O", 0, "O")
    N3_coord = calculateCoordinates(N2, C9, C10, N3_C10_length, N3_C10_C9_angle, N3_C10_C9_N2_diangle)
    N3 = Atom("N3", N3_coord, 0.0, 1.0, " ", " N", 0, "N")
    C11_coord = calculateCoordinates(C9, C10, N3, C11_N3_length, C11_N3_C10_angle, C11_N3_C10_C9_diangle)
    C11 = Atom("C11", C11_coord, 0.0, 1.0, " ", " CG", 0, "C")
    C12_coord = calculateCoordinates(C10, N3, C11, C12_C11_length, C12_C11_N3_angle, C12_C11_N3_C10_diangle)
    C12 = Atom("C12", C12_coord, 0.0, 1.0, " ", " CB", 0, "C")
    C13_coord = calculateCoordinates(N3, C11, C12, C13_C12_length, C13_C12_C11_angle, C13_C12_C11_N3_diangle)
    C13 = Atom("C13", C13_coord, 0.0, 1.0, " ", " CA", 0, "C")
    C4_coord = calculateCoordinates(C11, C12, C13, geo.C4_C13_length, geo.C4_C13_C12_angle, geo.C4_C13_C12_C11_diangle)
    C4 = Atom("C4", C4_coord, 0.0, 1.0, " ", " C", 0, "C")
    O2_coord = calculateCoordinates(C12, C13, C4, geo.O2_C4_length, geo.O2_C4_C13_angle, geo.O2_C4_C13_C12_diangle)
    O2 = Atom("O2", O2_coord, 0.0, 1.0, " ", " O", 0, "O")
    res = make_res_of_type_linker(segID, N1, C5, C6, C7, C8, O3, N2, C9, C10, O4, N3, C11, C12, C13, C4, O2, geo)
    structure[0]["A"].add(res)
    return res

def add_residue_alalinker(
        structure: Structure, residue: Union[Geo, str], phi=-120, psi_im1=140, omega=-370
) -> Structure:


    if isinstance(residue, Geo):
        geo = residue
    elif isinstance(residue, str):
        geo = geometry(residue)
        geo.phi = phi
        geo.psi_im1 = psi_im1
        if omega > -361:
            geo.omega = omega
    else:
        raise ValueError("Invalid residue argument:", residue)

    return add_residue_from_geo_alalinker(structure, geo)
def add_residue_from_geo_linker_ala(structure: Structure, geo: Geo) -> Structure:

    resRef = getReferenceResidue(structure)
    AA = geo.residue_name
    segID = resRef.get_id()[1]
    segID += 1


    N_coord = calculateCoordinates(
        resRef["C12"], resRef["C13"], resRef["C4"], geo.N_C4_length, geo.N_C4_C13_angle, geo.N_C4_C13_C12_diangle
    )
    N = Atom("N", N_coord, 0.0, 1.0, " ", " N", 0, "N")

    CA_coord = calculateCoordinates(
        resRef["C13"], resRef["C4"], N, geo.CA_N_length, geo.CA_N_C4_angle, geo.CA_N_C4_C13_diangle
    )
    CA = Atom("CA", CA_coord, 0.0, 1.0, " ", " CA", 0, "C")

    C_coord = calculateCoordinates(resRef["C4"], N, CA, geo.C_CA_length, geo.C_CA_N_angle, geo.C_CA_N_C4_diangle)
    C = Atom("C", C_coord, 0.0, 1.0, " ", " C", 0, "C")

    ##Create Carbonyl atom (to be moved later)

    carbonyl = calculateCoordinates(
        N, CA, C, geo.C_O_length, geo.CA_C_O_angle, geo.N_CA_C_O_diangle
    )
    O = Atom("O", carbonyl, 0.0, 1.0, " ", " O", 0, "O")

    res = make_res_of_type_natural(segID, N, CA, C, O, geo)


    structure[0]["A"].add(res)
    return structure
def add_residue_linker_ala(
        structure: Structure, residue: Union[Geo, str], phi=-120, psi_im1=140, omega=-370
) -> Structure:

    if isinstance(residue, Geo):
        geo = residue
    elif isinstance(residue, str):
        geo = geometry(residue)
        geo.phi = phi
        geo.psi_im1 = psi_im1
        if omega > -361:
            geo.omega = omega
    else:
        raise ValueError("Invalid residue argument:", residue)

    return add_residue_from_geo_linker_ala(structure, geo)
# right
def add_residue_from_geo(structure: Structure, geo: Geo) -> Structure:
    """Adds a residue to chain A model 0 of the given structure, and
    returns the new structure. The residue to be added is determined by
    the geometry object given as second argument.

    This function is a helper function and should not normally be called
    directly. Call add_residue() instead."""
    resRef = getReferenceResidue(structure)
    AA = geo.residue_name
    segID = resRef.get_id()[1]
    segID += 1

    ##geometry to bring together residue
    peptide_bond = geo.peptide_bond
    CA_C_N_angle = geo.CA_C_N_angle

    ##Backbone Coordinates

    CG_NB_CA_C_diangle1 = geo.CG_NB_CA_C_diangle1
    NB_CA_C_N_diangle = geo.NB_CA_C_N_diangle

    a = geo.a
    c = geo.c
    N_CD1_CG_NB_diangle = geo.N_CD1_CG_NB_diangle

    CA_NB_length = geo.CA_NB_length
    CA_C_length = geo.CA_C_length
    NB_CA_C_angle = geo.NB_CA_C_angle

    CA_C_N_angle = geo.CA_C_N_angle

    C_N_CD1_angle = geo.C_N_CD1_angle

    N_CD1_length = geo.N_CD1_length
    N_CD1_CG_angle = geo.N_CD1_CG_angle

    CD1_CG_length = geo.CD1_CG_length
    CD1_CG_NB_angle = geo.CD1_CG_NB_angle

    CG_NB_length = geo.CG_NB_length
    CG_NB_CA_angle = geo.CG_NB_CA_angle
    CA_C_N_CD1_diangle = geo.CA_C_N_CD1_diangle

    N_coord = calculateCoordinates(
        resRef["NB"], resRef["CA"], resRef["C"], peptide_bond, CA_C_N_angle, NB_CA_C_N_diangle
    )
    N = Atom("N", N_coord, 0.0, 1.0, " ", " N", 0, "N")

    CD1_coord = calculateCoordinates(
        resRef["CA"], resRef["C"], N, N_CD1_length, C_N_CD1_angle, CA_C_N_CD1_diangle
    )
    CD1 = Atom("CD1", CD1_coord, 0.0, 1.0, " ", " CD1", 0, "C")

    CG_coord = calculateCoordinates(resRef["C"], N, CD1, CD1_CG_length, N_CD1_CG_angle, c)
    CG = Atom("CG", CG_coord, 0.0, 1.0, " ", " CG", 0, "C")

    NB = calculateCoordinates(
        N, CD1, CG, CG_NB_length, CD1_CG_NB_angle, N_CD1_CG_NB_diangle
    )
    NB = Atom("NB", NB, 0.0, 1.0, " ", " NB", 0, "N")
    carbon_a = calculateCoordinates(
        CD1, CG, NB, CA_NB_length, CG_NB_CA_angle, a
    )
    CA = Atom("CA", carbon_a, 0.0, 1.0, " ", " CA", 0, "C")
    carbon = calculateCoordinates(
        CG, NB, CA, CA_C_length, NB_CA_C_angle, CG_NB_CA_C_diangle1
    )
    C = Atom("C", carbon, 0.0, 1.0, " ", " C", 0, "C")
    ##Create Carbonyl atom (to be moved later)
    C_O_length = geo.C_O_length
    CA_C_O_angle = geo.CA_C_O_angle
    NB_CA_C_O_diangle1 = geo.NB_CA_C_O_diangle1

    carbonyl = calculateCoordinates(
        NB, CA, C, C_O_length, CA_C_O_angle, NB_CA_C_O_diangle1
    )
    O = Atom("O", carbonyl, 0.0, 1.0, " ", " O", 0, "O")

    res = make_res_of_type_aa(segID, N, CD1, CG, NB, CA, C, O, geo)

    structure[0]["A"].add(res)
    return structure

# AA_AA
def add_residue_from_geo_AA_AA(structure: Structure, geo: Geo) -> Structure:
    """Adds a residue to chain A model 0 of the given structure, and
    returns the new structure. The residue to be added is determined by
    the geometry object given as second argument.

    This function is a helper function and should not normally be called
    directly. Call add_residue() instead."""
    resRef = getReferenceResidue(structure)
    AA = geo.residue_name
    segID = resRef.get_id()[1]
    segID += 1

    N_C_length = geo.N_C_length
    N_C_CA_angle = geo.N_C_CA_angle
    N_C_CA_NB_diangle = geo.N_C_CA_NB_diangle

    CD1_N_length = geo.CD1_N_length
    CD1_N_C_angle = geo.CD1_N_C_angle
    CD1_N_C_CA_diangle = geo.CD1_N_C_CA_diangle

    CG_CD1_length = geo.CG_CD1_length
    CG_CD1_N_angle = geo.CG_CD1_N_angle
    CG_CD1_N_C_diangle = geo.CG_CD1_N_C_diangle

    CG_NB_length = geo.NB_CG_length
    CD1_CG_NB_angle = geo.NB_CG_CD1_angle
    N_CD1_CG_NB_diangle = geo.NB_CG_CD1_N_diangle

    CA_NB_length = geo.CA_NB_length
    CG_NB_CA_angle = geo.CA_NB_CG_angle
    CA_NB_CG_CD1_diangle = geo.CA_NB_CG_CD1_diangle

    CA_C_length = geo.C_CA_length
    NB_CA_C_angle = geo.C_CA_NB_angle
    CG_NB_CA_C_diangle = geo.C_CA_NB_CG_diangle

    N_coord = calculateCoordinates(
        resRef["NB"], resRef["CA"], resRef["C"], N_C_length, N_C_CA_angle, N_C_CA_NB_diangle
    )
    N = Atom("N", N_coord, 0.0, 1.0, " ", " N", 0, "N")

    CD1_coord = calculateCoordinates(
        resRef["CA"], resRef["C"], N, CD1_N_length, CD1_N_C_angle, CD1_N_C_CA_diangle
    )
    CD1 = Atom("CD1", CD1_coord, 0.0, 1.0, " ", " CD1", 0, "C")

    CG_coord = calculateCoordinates(resRef["C"], N, CD1, CG_CD1_length, CG_CD1_N_angle, CG_CD1_N_C_diangle)
    CG = Atom("CG", CG_coord, 0.0, 1.0, " ", " CG", 0, "C")

    NB = calculateCoordinates(
        N, CD1, CG, CG_NB_length, CD1_CG_NB_angle, N_CD1_CG_NB_diangle
    )
    NB = Atom("NB", NB, 0.0, 1.0, " ", " NB", 0, "N")
    carbon_a = calculateCoordinates(
        CD1, CG, NB, CA_NB_length, CG_NB_CA_angle, CA_NB_CG_CD1_diangle
    )
    CA = Atom("CA", carbon_a, 0.0, 1.0, " ", " CA", 0, "C")
    carbon = calculateCoordinates(
        CG, NB, CA, CA_C_length, NB_CA_C_angle, CG_NB_CA_C_diangle
    )
    C = Atom("C", carbon, 0.0, 1.0, " ", " C", 0, "C")
    ##Create Carbonyl atom (to be moved later)
    C_O_length = geo.C_O_length
    CA_C_O_angle = geo.CA_C_O_angle
    NB_CA_C_O_diangle = geo.NB_CA_C_O_diangle

    carbonyl = calculateCoordinates(
        NB, CA, C, C_O_length, CA_C_O_angle, NB_CA_C_O_diangle
    )
    O = Atom("O", carbonyl, 0.0, 1.0, " ", " O", 0, "O")

    res = make_res_of_type_aa(segID, N, CD1, CG, NB, CA, C, O, geo)

    structure[0]["A"].add(res)
    return structure


# aa_linker
def add_residue_from_geo_aa_linker2_1(structure: Structure, geo: Geo) -> Structure:
    """Adds a residue to chain A model 0 of the given structure, and
    returns the new structure. The residue to be added is determined by
    the geometry object given as second argument.

    This function is a helper function and should not normally be called
    directly. Call add_residue() instead."""
    resRef = getReferenceResidue(structure)
    AA = geo.residue_name
    segID = resRef.get_id()[1]
    segID += 1

    NL_C_length = geo.NL_C_length
    NL_C_CA_angle = geo.NL_C_CA_angle
    NL_C_CA_NB_diangle = geo.NL_C_CA_NB_diangle

    C1_NL_length = geo.C1_NL_length
    C1_NL_C_angle = geo.C1_NL_C_angle
    C1_NL_C_CA_diangle = geo.C1_NL_C_CA_diangle

    C2_C1_length = geo.C2_C1_length
    C2_C1_NL_angle = geo.C2_C1_NL_angle
    C2_C1_NL_C_diangle = geo.C2_C1_NL_C_diangle

    C3_C2_length = geo.C3_C2_length
    C3_C2_C1_angle = geo.C3_C2_C1_angle
    C3_C2_C1_NL_diangle = geo.C3_C2_C1_NL_diangle

    C4_C3_length = geo.C4_C3_length
    C4_C3_C2_angle = geo.C4_C3_C2_angle
    C4_C3_C2_C1_diangle = geo.C4_C3_C2_C1_diangle

    N2_C4_length = geo.N2_C4_length
    N2_C4_C3_angle = geo.N2_C4_C3_angle
    N2_C4_C3_C2_diangle = geo.N2_C4_C3_C2_diangle

    C5_N2_length = geo.C5_N2_length
    C5_N2_C4_angle = geo.C5_N2_C4_angle
    C5_N2_C4_C3_diangle = geo.C5_N2_C4_C3_diangle

    C6_C5_length = geo.C6_C5_length
    C6_C5_N2_angle = geo.C6_C5_N2_angle
    C6_C5_N2_C4_diangle = geo.C6_C5_N2_C4_diangle

    N3_C6_length = geo.N3_C6_length
    N3_C6_C5_angle = geo.N3_C6_C5_angle
    N3_C6_C5_N2_diangle = geo.N3_C6_C5_N2_diangle

    C7_N3_length = geo.C7_N3_length
    C7_N3_C6_angle = geo.C7_N3_C6_angle
    C7_N3_C6_C5_diangle = geo.C7_N3_C6_C5_diangle

    C8_C7_length = geo.C8_C7_length
    C8_C7_N3_angle = geo.C8_C7_N3_angle
    C8_C7_N3_C6_diangle = geo.C8_C7_N3_C6_diangle

    N4_C8_length = geo.N4_C8_length
    N4_C8_C7_angle = geo.N4_C8_C7_angle
    N4_C8_C7_N3_diangle = geo.N4_C8_C7_N3_diangle

    C13_N4_length = geo.C13_N4_length
    C13_N4_C8_angle = geo.C13_N4_C8_angle
    C13_N4_C8_C7_diangle = geo.C13_N4_C8_C7_diangle

    C14_C13_length = geo.C14_C13_length
    C14_C13_N4_angle = geo.C14_C13_N4_angle
    C14_C13_N4_C8_diangle = geo.C14_C13_N4_C8_diangle

    C15_C14_length = geo.C15_C14_length
    C15_C14_C13_angle = geo.C15_C14_C13_angle
    C15_C14_C13_N4_diangle = geo.C15_C14_C13_N4_diangle

    CL_C15_length = geo.CL_C15_length
    CL_C15_C14_angle = geo.CL_C15_C14_angle
    CL_C15_C14_C13_diangle = geo.CL_C15_C14_C13_diangle

    N_coord = calculateCoordinates(
        resRef["NB"], resRef["CA"], resRef["C"], NL_C_length, NL_C_CA_angle, NL_C_CA_NB_diangle
    )
    N = Atom("N", N_coord, 0.0, 1.0, " ", " N", 0, "N")

    C1_coord = calculateCoordinates(
        resRef["CA"], resRef["C"], N, C1_NL_length, C1_NL_C_angle, C1_NL_C_CA_diangle
    )
    C1 = Atom("C1", C1_coord, 0.0, 1.0, " ", " C1", 0, "C")

    C2_coord = calculateCoordinates(resRef["C"], N, C1, C2_C1_length, C2_C1_NL_angle, C2_C1_NL_C_diangle)
    C2 = Atom("C2", C2_coord, 0.0, 1.0, " ", " C2", 0, "C")

    C3_coord = calculateCoordinates(N, C1, C2, C3_C2_length, C3_C2_C1_angle, C3_C2_C1_NL_diangle)
    C3 = Atom("C3", C3_coord, 0.0, 1.0, " ", " C3", 0, "C")
    C4_coord = calculateCoordinates(C1, C2, C3, C4_C3_length, C4_C3_C2_angle, C4_C3_C2_C1_diangle)
    C4 = Atom("C4", C4_coord, 0.0, 1.0, " ", " C4", 0, "C")
    O1_coord = calculateCoordinates(C2, C3, C4, geo.O1_C4_length, geo.O1_C4_C3_angle, geo.O1_C4_C3_C2_diangle)
    O1 = Atom("O1", O1_coord, 0.0, 1.0, " ", " O1", 0, "O")
    N2_coord = calculateCoordinates(C2, C3, C4, N2_C4_length, N2_C4_C3_angle, N2_C4_C3_C2_diangle)
    N2 = Atom("N2", N2_coord, 0.0, 1.0, " ", " N2", 0, "N")
    C5_coord = calculateCoordinates(C3, C4, N2, C5_N2_length, C5_N2_C4_angle, C5_N2_C4_C3_diangle)
    C5 = Atom("C5", C5_coord, 0.0, 1.0, " ", " C5", 0, "C")
    C6_coord = calculateCoordinates(C4, N2, C5, C6_C5_length, C6_C5_N2_angle, C6_C5_N2_C4_diangle)
    C6 = Atom("C6", C6_coord, 0.0, 1.0, " ", " C6", 0, "C")
    N3_coord = calculateCoordinates(N2, C5, C6, N3_C6_length, N3_C6_C5_angle, N3_C6_C5_N2_diangle)
    N3 = Atom("N3", N3_coord, 0.0, 1.0, " ", " N3", 0, "N")
    C7_coord = calculateCoordinates(C5, C6, N3, C7_N3_length, C7_N3_C6_angle, C7_N3_C6_C5_diangle)
    C7 = Atom("C7", C7_coord, 0.0, 1.0, " ", " C7", 0, "C")
    C8_coord = calculateCoordinates(C6, N3, C7, C8_C7_length, C8_C7_N3_angle, C8_C7_N3_C6_diangle)
    C8 = Atom("C8", C8_coord, 0.0, 1.0, " ", " C8", 0, "C")
    O2_coord = calculateCoordinates(N3, C7, C8, geo.O2_C8_length, geo.O2_C8_C7_angle, geo.O2_C8_C7_N3_diangle)
    O2 = Atom("O2", O2_coord, 0.0, 1.0, " ", " O2", 0, "O")
    N4_coord = calculateCoordinates(N3, C7, C8, N4_C8_length, N4_C8_C7_angle, N4_C8_C7_N3_diangle)
    N4 = Atom("N4", N4_coord, 0.0, 1.0, " ", " N4", 0, "N")
    C13_coord = calculateCoordinates(C7, C8, N4, C13_N4_length, C13_N4_C8_angle, C13_N4_C8_C7_diangle)
    C13 = Atom("C13", C13_coord, 0.0, 1.0, " ", " C13", 0, "C")
    C14_coord = calculateCoordinates(C8, N4, C13, C14_C13_length, C14_C13_N4_angle, C14_C13_N4_C8_diangle)
    C14 = Atom("C14", C14_coord, 0.0, 1.0, " ", " C14", 0, "C")
    CA_coord = calculateCoordinates(N4, C13, C14, C15_C14_length, C15_C14_C13_angle, C15_C14_C13_N4_diangle)
    CA = Atom("CA", CA_coord, 0.0, 1.0, " ", " CA", 0, "C")
    C_coord = calculateCoordinates(C13, C14, CA, CL_C15_length, CL_C15_C14_angle, CL_C15_C14_C13_diangle)
    C = Atom("C", C_coord, 0.0, 1.0, " ", " C", 0, "C")
    O_coord = calculateCoordinates(C14, CA, C, geo.O3_CL_length, geo.O3_CL_C15_angle, geo.O3_CL_C15_C14_diangle)
    O = Atom("O", O_coord, 0.0, 1.0, " ", " O", 0, "O")

    res = make_res_of_type_linker2_1(segID, N, C1, C2, C3, C4, O1, N2, C5, C6, N3, C7, C8, O2, N4, C13,
                                     C14, CA, C, O,geo)
    structure[0]["A"].add(res)
    return structure

def add_residue_from_geo_aa_linker2_3(structure: Structure, geo: Geo) -> Structure:
    """Adds a residue to chain A model 0 of the given structure, and
    returns the new structure. The residue to be added is determined by
    the geometry object given as second argument.

    This function is a helper function and should not normally be called
    directly. Call add_residue() instead."""
    resRef = getReferenceResidue(structure)
    AA = geo.residue_name
    segID = resRef.get_id()[1]
    segID += 1

    NL_coord = calculateCoordinates(
        resRef["NB"], resRef["CA"], resRef["C"], geo.NL_C_length, geo.NL_C_CA_angle, geo.NL_C_CA_NB_diangle
    )
    NL = Atom("NL", NL_coord, 0.0, 1.0, " ", " NL", 0, "N")

    C1_coord = calculateCoordinates(
        resRef["CA"], resRef["C"], NL, geo.C1_NL_length, geo.C1_NL_C_angle, geo.C1_NL_C_CA_diangle
    )
    C1 = Atom("C1", C1_coord, 0.0, 1.0, " ", " C1", 0, "C")

    C2_coord = calculateCoordinates(resRef["C"], NL, C1, geo.C2_C1_length, geo.C2_C1_NL_angle, geo.C2_C1_NL_C_diangle)
    C2 = Atom("C2", C2_coord, 0.0, 1.0, " ", " C2", 0, "C")

    C3_coord = calculateCoordinates(NL, C1, C2, geo.C3_C2_length, geo.C3_C2_C1_angle, geo.C3_C2_C1_NL_diangle)
    C3 = Atom("C3", C3_coord, 0.0, 1.0, " ", " C3", 0, "C")
    C4_coord = calculateCoordinates(C1, C2, C3, geo.C4_C3_length, geo.C4_C3_C2_angle,geo.C4_C3_C2_C1_diangle)
    C4 = Atom("C4", C4_coord, 0.0, 1.0, " ", " C4", 0, "C")
    O1_coord = calculateCoordinates(C2, C3, C4, geo.O1_C4_length, geo.O1_C4_C3_angle, geo.O1_C4_C3_C2_diangle)
    O1 = Atom("O1", O1_coord, 0.0, 1.0, " ", " O1", 0, "O")
    N2_coord = calculateCoordinates(C2, C3, C4, geo.N2_C4_length, geo.N2_C4_C3_angle, geo.N2_C4_C3_C2_diangle)
    N2 = Atom("N2", N2_coord, 0.0, 1.0, " ", " N2", 0, "N")
    C5_coord = calculateCoordinates(C3, C4, N2, geo.C5_N2_length, geo.C5_N2_C4_angle, geo.C5_N2_C4_C3_diangle)
    C5 = Atom("C5", C5_coord, 0.0, 1.0, " ", " C5", 0, "C")
    C6_coord = calculateCoordinates(C4, N2, C5, geo.C6_C5_length, geo.C6_C5_N2_angle, geo.C6_C5_N2_C4_diangle)
    C6 = Atom("C6", C6_coord, 0.0, 1.0, " ", " C6", 0, "C")
    N3_coord = calculateCoordinates(N2, C5, C6, geo.N3_C6_length, geo.N3_C6_C5_angle, geo.N3_C6_C5_N2_diangle)
    N3 = Atom("N3", N3_coord, 0.0, 1.0, " ", " N3", 0, "N")
    C7_coord = calculateCoordinates(C5, C6, N3, geo.C7_N3_length, geo.C7_N3_C6_angle, geo.C7_N3_C6_C5_diangle)
    C7 = Atom("C7", C7_coord, 0.0, 1.0, " ", " C7", 0, "C")
    C8_coord = calculateCoordinates(C6, N3, C7, geo.C8_C7_length, geo.C8_C7_N3_angle, geo.C8_C7_N3_C6_diangle)
    C8 = Atom("C8", C8_coord, 0.0, 1.0, " ", " C8", 0, "C")
    O2_coord = calculateCoordinates(N3, C7, C8, geo.O2_C8_length, geo.O2_C8_C7_angle, geo.O2_C8_C7_N3_diangle)
    O2 = Atom("O2", O2_coord, 0.0, 1.0, " ", " O2", 0, "O")
    N4_coord = calculateCoordinates(N3, C7, C8, geo.N4_C8_length, geo.N4_C8_C7_angle, geo.N4_C8_C7_N3_diangle)
    N4 = Atom("N4", N4_coord, 0.0, 1.0, " ", " N4", 0, "N")
    C13_coord = calculateCoordinates(C7, C8, N4, geo.C13_N4_length, geo.C13_N4_C8_angle, geo.C13_N4_C8_C7_diangle)
    C13 = Atom("C13", C13_coord, 0.0, 1.0, " ", " C13", 0, "C")
    C14_coord = calculateCoordinates(C8, N4, C13, geo.C14_C13_length, geo.C14_C13_N4_angle, geo.C14_C13_N4_C8_diangle)
    C14 = Atom("C14", C14_coord, 0.0, 1.0, " ", " C14", 0, "C")
    C15_coord = calculateCoordinates(N4, C13, C14, geo.C15_C14_length, geo.C15_C14_C13_angle,
                                     geo.C15_C14_C13_N4_diangle)
    C15 = Atom("C15", C15_coord, 0.0, 1.0, " ", " C15", 0, "C")
    C16_coord = calculateCoordinates(C13, C14, C15, geo.C16_C15_length, geo.C16_C15_C14_angle,
                                     geo.C16_C15_C14_C13_diangle)
    C16 = Atom("C16", C16_coord, 0.0, 1.0, " ", " C16", 0, "C")
    C17_coord = calculateCoordinates(C14, C15, C16, geo.C17_C16_length, geo.C17_C16_C15_angle,
                                     geo.C17_C16_C15_C14_diangle)
    C17 = Atom("C17", C17_coord, 0.0, 1.0, " ", " C17", 0, "C")
    CL_coord = calculateCoordinates(C15, C16, C17,geo.CL_C17_length, geo.CL_C17_C16_angle,
                                     geo.CL_C17_C16_C15_diangle)
    CL = Atom("CL", CL_coord, 0.0, 1.0, " ", " CL", 0, "C")
    O3_coord = calculateCoordinates(C16, C17, CL, geo.O3_CL_length, geo.O3_CL_C17_angle, geo.O3_CL_C17_C16_diangle)
    O3 = Atom("O3", O3_coord, 0.0, 1.0, " ", " O3", 0, "O")
    res = make_res_of_type_linker2_3(segID, NL, C1, C2, C3, C4, O1, N2, C5, C6, N3, C7, C8, O2, N4, C13, C14,
                                     C15, C16, C17, CL, O3, geo)
    structure[0]["A"].add(res)
    return structure

def add_residue_from_geo_linker2_1_aa(structure: Structure, geo: Geo) -> Structure:
    """Adds a residue to chain A model 0 of the given structure, and
    returns the new structure. The residue to be added is determined by
    the geometry object given as second argument.

    This function is a helper function and should not normally be called
    directly. Call add_residue() instead."""
    resRef = getReferenceResidue(structure)
    AA = geo.residue_name
    segID = resRef.get_id()[1]
    segID += 1

    N_CL_length = geo.N_CL_length
    N_CL_C15_angle = geo.N_CL_C15_angle
    N_CL_C15_C14_diangle = geo.N_CL_C15_C14_diangle

    N_CD1_length = geo.N_CD1_length
    CD1_N_CL_angle = geo.CD1_N_CL_angle
    CD1_N_CL_C15_diangle = geo.CD1_N_CL_C15_diangle

    CG_CD1_length = geo.CD1_CG_length
    CG_CD1_N_angle = geo.N_CD1_CG_angle
    CG_CD1_N_CL_diangle = geo.CG_CD1_N_CL_diangle

    CG_NB_length = geo.CG_NB_length
    CD1_CG_NB_angle = geo.CD1_CG_NB_angle
    N_CD1_CG_NB_diangle = geo.N_CD1_CG_NB_diangle

    CA_NB_length = geo.CA_NB_length
    CG_NB_CA_angle = geo.CG_NB_CA_angle
    a1 = geo.a1

    CA_C_length = geo.CA_C_length
    NB_CA_C_angle = geo.NB_CA_C_angle
    CG_NB_CA_C_diangle = geo.CG_NB_CA_C_diangle
    N_coord = calculateCoordinates(
        resRef["C14"], resRef["CA"], resRef["C"], N_CL_length, N_CL_C15_angle, N_CL_C15_C14_diangle
    )
    N = Atom("N", N_coord, 0.0, 1.0, " ", " N", 0, "N")

    CD1_coord = calculateCoordinates(
        resRef["CA"], resRef["C"], N, N_CD1_length, CD1_N_CL_angle, CD1_N_CL_C15_diangle
    )
    CD1 = Atom("CD1", CD1_coord, 0.0, 1.0, " ", " CD1", 0, "C")

    CG_coord = calculateCoordinates(resRef["C"], N, CD1, CG_CD1_length, CG_CD1_N_angle, CG_CD1_N_CL_diangle)
    CG = Atom("CG", CG_coord, 0.0, 1.0, " ", " CG", 0, "C")

    NB = calculateCoordinates(
        N, CD1, CG, CG_NB_length, CD1_CG_NB_angle, N_CD1_CG_NB_diangle
    )
    NB = Atom("NB", NB, 0.0, 1.0, " ", " NB", 0, "N")
    carbon_a = calculateCoordinates(
        CD1, CG, NB, CA_NB_length, CG_NB_CA_angle, a1
    )
    CA = Atom("CA", carbon_a, 0.0, 1.0, " ", " CA", 0, "C")
    carbon = calculateCoordinates(
        CG, NB, CA, CA_C_length, NB_CA_C_angle, CG_NB_CA_C_diangle
    )
    C = Atom("C", carbon, 0.0, 1.0, " ", " C", 0, "C")
    C_O_length = geo.C_O_length
    CA_C_O_angle = geo.CA_C_O_angle
    NB_CA_C_O_diangle = geo.NB_CA_C_O_diangle

    carbonyl = calculateCoordinates(
        NB, CA, C, C_O_length, CA_C_O_angle, NB_CA_C_O_diangle
    )
    O = Atom("O", carbonyl, 0.0, 1.0, " ", " O", 0, "O")

    res = make_res_of_type_aa(segID, N, CD1, CG, NB, CA, C, O, geo)

    structure[0]["A"].add(res)
    return structure
def add_residue_from_geo_linker2_3_aa(structure: Structure, geo: Geo) -> Structure:
    """Adds a residue to chain A model 0 of the given structure, and
    returns the new structure. The residue to be added is determined by
    the geometry object given as second argument.

    This function is a helper function and should not normally be called
    directly. Call add_residue() instead."""
    resRef = getReferenceResidue(structure)
    AA = geo.residue_name
    segID = resRef.get_id()[1]
    segID += 1

    N_coord = calculateCoordinates(
        resRef["C16"], resRef["C17"], resRef["CL"], geo.N_CL_length, geo.N_CL_C15_angle, geo.N_CL_C15_C14_diangle
    )
    N = Atom("N", N_coord, 0.0, 1.0, " ", " N", 0, "N")

    CD1_coord = calculateCoordinates(
        resRef["C17"], resRef["CL"], N, geo.N_CD1_length, geo.CD1_N_CL_angle, geo.CD1_N_CL_C15_diangle
    )
    CD1 = Atom("CD1", CD1_coord, 0.0, 1.0, " ", " CD1", 0, "C")

    CG_coord = calculateCoordinates(resRef["CL"], N, CD1, geo.CD1_CG_length, geo.N_CD1_CG_angle, geo.CG_CD1_N_CL_diangle)
    CG = Atom("CG", CG_coord, 0.0, 1.0, " ", " CG", 0, "C")

    NB = calculateCoordinates(
        N, CD1, CG, geo.CG_NB_length, geo.CD1_CG_NB_angle, geo.N_CD1_CG_NB_diangle
    )
    NB = Atom("NB", NB, 0.0, 1.0, " ", " NB", 0, "N")
    carbon_a = calculateCoordinates(
        CD1, CG, NB, geo.CA_NB_length, geo.CG_NB_CA_angle, geo.a1
    )
    CA = Atom("CA", carbon_a, 0.0, 1.0, " ", " CA", 0, "C")
    carbon = calculateCoordinates(
        CG, NB, CA, geo.CA_C_length, geo.NB_CA_C_angle, geo.CG_NB_CA_C_diangle
    )
    C = Atom("C", carbon, 0.0, 1.0, " ", " C", 0, "C")

    carbonyl = calculateCoordinates(
        NB, CA, C, geo.C_O_length, geo.CA_C_O_angle, geo.NB_CA_C_O_diangle
    )
    O = Atom("O", carbonyl, 0.0, 1.0, " ", " O", 0, "O")

    res = make_res_of_type_aa(segID, N, CD1, CG, NB, CA, C, O, geo)
    structure[0]["A"].add(res)
    return structure

def make_extended_structure(AA_chain: str) -> Structure:
    """Place a sequence of amino acids into a peptide in the extended
    conformation. The argument AA_chain holds the sequence of amino
    acids to be used."""
    geo = geometry(AA_chain[0])
    struc = initialize_res(geo)

    for i in range(1, len(AA_chain)):
        AA = AA_chain[i]
        geo = geometry(AA)
        add_residue(struc, geo)

    return struc


def add_residue(
        structure: Structure, residue: Union[Geo, str], phi=-120, psi_im1=140, omega=-370
) -> Structure:
    """Adds a residue to chain A model 0 of the given structure, and
    returns the new structure. The residue to be added can be specified
    in two ways: either as a geometry object (in which case
    the remaining arguments phi, psi_im1, and omega are ignored) or as a
    single-letter amino-acid code. In the latter case, the optional
    arguments phi, psi_im1, and omega specify the corresponding backbone
    angles.

    When omega is specified, it needs to be a value greater than or equal
    to -360. Values below -360 are ignored."""

    if isinstance(residue, Geo):
        geo = residue
    elif isinstance(residue, str):
        geo = geometry(residue)
        geo.phi = phi
        geo.psi_im1 = psi_im1
        if omega > -361:
            geo.omega = omega
    else:
        raise ValueError("Invalid residue argument:", residue)

    return add_residue_from_geo(structure, geo)


def add_residue_AA_AA(
        structure: Structure, residue: Union[Geo, str], phi=-120, psi_im1=140, omega=-370
) -> Structure:
    """Adds a residue to chain A model 0 of the given structure, and
    returns the new structure. The residue to be added can be specified
    in two ways: either as a geometry object (in which case
    the remaining arguments phi, psi_im1, and omega are ignored) or as a
    single-letter amino-acid code. In the latter case, the optional
    arguments phi, psi_im1, and omega specify the corresponding backbone
    angles.

    When omega is specified, it needs to be a value greater than or equal
    to -360. Values below -360 are ignored."""

    if isinstance(residue, Geo):
        geo = residue
    elif isinstance(residue, str):
        geo = geometry(residue)
        geo.phi = phi
        geo.psi_im1 = psi_im1
        if omega > -361:
            geo.omega = omega
    else:
        raise ValueError("Invalid residue argument:", residue)

    return add_residue_from_geo_AA_AA(structure, geo)


def add_residue_aa_linker2_1(
        structure: Structure, residue: Union[Geo, str], phi=-120, psi_im1=140, omega=-370
) -> Structure:
    """Adds a residue to chain A model 0 of the given structure, and
    returns the new structure. The residue to be added can be specified
    in two ways: either as a geometry object (in which case
    the remaining arguments phi, psi_im1, and omega are ignored) or as a
    single-letter amino-acid code. In the latter case, the optional
    arguments phi, psi_im1, and omega specify the corresponding backbone
    angles.

    When omega is specified, it needs to be a value greater than or equal
    to -360. Values below -360 are ignored."""

    if isinstance(residue, Geo):
        geo = residue
    elif isinstance(residue, str):
        geo = geometry(residue)
        geo.phi = phi
        geo.psi_im1 = psi_im1
        if omega > -361:
            geo.omega = omega
    else:
        raise ValueError("Invalid residue argument:", residue)

    return add_residue_from_geo_aa_linker2_1(structure, geo)

def add_residue_aa_linker2_3(
        structure: Structure, residue: Union[Geo, str], phi=-120, psi_im1=140, omega=-370
) -> Structure:
    """Adds a residue to chain A model 0 of the given structure, and
    returns the new structure. The residue to be added can be specified
    in two ways: either as a geometry object (in which case
    the remaining arguments phi, psi_im1, and omega are ignored) or as a
    single-letter amino-acid code. In the latter case, the optional
    arguments phi, psi_im1, and omega specify the corresponding backbone
    angles.

    When omega is specified, it needs to be a value greater than or equal
    to -360. Values below -360 are ignored."""

    if isinstance(residue, Geo):
        geo = residue
    elif isinstance(residue, str):
        geo = geometry(residue)
        geo.phi = phi
        geo.psi_im1 = psi_im1
        if omega > -361:
            geo.omega = omega
    else:
        raise ValueError("Invalid residue argument:", residue)

    return add_residue_from_geo_aa_linker2_3(structure, geo)

def add_residue_linker2_1_aa(
        structure: Structure, residue: Union[Geo, str], phi=-120, psi_im1=140, omega=-370
) -> Structure:
    """Adds a residue to chain A model 0 of the given structure, and
    returns the new structure. The residue to be added can be specified
    in two ways: either as a geometry object (in which case
    the remaining arguments phi, psi_im1, and omega are ignored) or as a
    single-letter amino-acid code. In the latter case, the optional
    arguments phi, psi_im1, and omega specify the corresponding backbone
    angles.

    When omega is specified, it needs to be a value greater than or equal
    to -360. Values below -360 are ignored."""

    if isinstance(residue, Geo):
        geo = residue
    elif isinstance(residue, str):
        geo = geometry(residue)
        geo.phi = phi
        geo.psi_im1 = psi_im1
        if omega > -361:
            geo.omega = omega
    else:
        raise ValueError("Invalid residue argument:", residue)

    return add_residue_from_geo_linker2_1_aa(structure, geo)
def add_residue_linker2_3_aa(
        structure: Structure, residue: Union[Geo, str], phi=-120, psi_im1=140, omega=-370
) -> Structure:
    """Adds a residue to chain A model 0 of the given structure, and
    returns the new structure. The residue to be added can be specified
    in two ways: either as a geometry object (in which case
    the remaining arguments phi, psi_im1, and omega are ignored) or as a
    single-letter amino-acid code. In the latter case, the optional
    arguments phi, psi_im1, and omega specify the corresponding backbone
    angles.

    When omega is specified, it needs to be a value greater than or equal
    to -360. Values below -360 are ignored."""

    if isinstance(residue, Geo):
        geo = residue
    elif isinstance(residue, str):
        geo = geometry(residue)
        geo.phi = phi
        geo.psi_im1 = psi_im1
        if omega > -361:
            geo.omega = omega
    else:
        raise ValueError("Invalid residue argument:", residue)

    return add_residue_from_geo_linker2_3_aa(structure, geo)


def make_structure(
        AA_chain: str, phi: List[float], psi_im1: List[float], omega: Optional[List] = None
) -> Structure:
    """Place a sequence of amino acids into a peptide with specified
    backbone dihedral angles. The argument AA_chain holds the
    sequence of amino acids to be used. The arguments phi and psi_im1 hold
    lists of backbone angles, one for each amino acid, *starting from
    the second amino acid in the chain*. The argument
    omega (optional) holds a list of omega angles, also starting from
    the second amino acid in the chain."""
    geo = geometry(AA_chain[0])
    struc = initialize_res(geo)

    if omega is None or not len(omega):
        for i in range(1, len(AA_chain)):
            AA = AA_chain[i]
            add_residue(struc, AA, phi[i - 1], psi_im1[i - 1])
    else:
        for i in range(1, len(AA_chain)):
            AA = AA_chain[i]
            add_residue(struc, AA, phi[i - 1], psi_im1[i - 1], omega[i - 1])

    return struc


def make_structure_from_geos(geos: List[Geo]) -> Structure:
    """Creates a structure out of a list of geometry objects."""
    model_structure = initialize_res(geos[0])
    for i in range(1, len(geos)):
        add_residue(model_structure, geos[i])

    return model_structure


def add_terminal_OXT(structure: Structure, C_OXT_length: float = 1.23) -> Structure:
    """Adds a terminal oxygen atom ('OXT') to the last residue of chain A model 0 of the given structure,
    and returns the new structure. The OXT atom object will be contained in the last residue object of the structure.

This function should be used only when the structure object is completed and no further residues need to be appended."""

    rad = 180.0 / math.pi

    # obtain last residue infomation
    resRef = getReferenceResidue(structure)
    N_resRef = resRef["N"]
    CA_resRef = resRef["CA"]
    C_resRef = resRef["C"]
    O_resRef = resRef["O"]

    n_vec = N_resRef.get_vector()
    ca_vec = CA_resRef.get_vector()
    c_vec = C_resRef.get_vector()
    o_vec = O_resRef.get_vector()

    # geometry to bring together residue
    CA_C_OXT_angle = calc_angle(ca_vec, c_vec, o_vec) * rad
    N_CA_C_O_diangle = calc_dihedral(n_vec, ca_vec, c_vec, o_vec) * rad
    N_CA_C_OXT_diangle = N_CA_C_O_diangle - 180.0
    if N_CA_C_O_diangle < 0:
        N_CA_C_OXT_diangle = N_CA_C_O_diangle + 180.0

    # OXT atom creation
    OXT_coord = calculateCoordinates(
        N_resRef, CA_resRef, C_resRef, C_OXT_length, CA_C_OXT_angle, N_CA_C_OXT_diangle
    )
    OXT = Atom("OXT", OXT_coord, 0.0, 1.0, " ", "OXT", 0, "O")

    # modify last residue of the structure to contain the OXT atom
    resRef.add(OXT)
    return structure
