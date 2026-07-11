"""Documented geographic and building-use classifications for BBR rows."""

from __future__ import annotations

import polars as pl


# Danmarks Statistik: NUTS_V1_2007_DK, valid from 1 January 2007.
# https://www.dst.dk/da/Statistik/dokumentation/nomenklaturer/nuts
MUNICIPALITY_CODES_BY_REGION = {
    "Region Hovedstaden": (
        101,
        147,
        151,
        153,
        155,
        157,
        159,
        161,
        163,
        165,
        167,
        169,
        173,
        175,
        183,
        185,
        187,
        190,
        201,
        210,
        217,
        219,
        223,
        230,
        240,
        250,
        260,
        270,
        400,
        411,
    ),
    "Region Sjælland": (
        253,
        259,
        265,
        269,
        306,
        316,
        320,
        326,
        329,
        330,
        336,
        340,
        350,
        360,
        370,
        376,
        390,
    ),
    "Region Syddanmark": (
        410,
        420,
        430,
        440,
        450,
        461,
        479,
        480,
        482,
        492,
        510,
        530,
        540,
        550,
        561,
        563,
        573,
        575,
        580,
        607,
        621,
        630,
    ),
    "Region Midtjylland": (
        615,
        657,
        661,
        665,
        671,
        706,
        707,
        710,
        727,
        730,
        740,
        741,
        746,
        751,
        756,
        760,
        766,
        779,
        791,
    ),
    "Region Nordjylland": (
        773,
        787,
        810,
        813,
        820,
        825,
        840,
        846,
        849,
        851,
        860,
    ),
}


# Fine aggregation of the official BBR BygAnvendelse hierarchy. It keeps the
# categories used in the bachelor pipeline separable so analyses can combine
# them into coarser literature classifications without rereading the raw CSV.
# https://teknik.bbr.dk/kodelister/0/1/0/BygAnvendelse
BUILDING_USE_CODES_BY_GROUP = {
    "Housing": (110, 120, 121, 122, 130, 131, 132, 140, 150, 160, 185, 190),
    "Agriculture": (210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 970),
    "Production & energy": (220, 221, 222, 223, 229, 230, 231, 232, 233, 234, 239, 290),
    "Transport": (310, 311, 312, 313, 314, 315, 319),
    "Commerce & services": (320, 321, 322, 323, 324, 325, 329, 330, 331, 332, 333, 334, 339, 390),
    "Institutions": (
        410,
        411,
        412,
        413,
        414,
        415,
        416,
        419,
        420,
        421,
        422,
        429,
        430,
        431,
        432,
        433,
        439,
        440,
        441,
        442,
        443,
        444,
        449,
        451,
        490,
    ),
    "Leisure": (510, 520, 521, 522, 523, 529, 530, 531, 532, 533, 534, 535, 539, 540, 585, 590),
    "Outbuildings & other": (910, 920, 930, 940, 950, 960, 990, 999),
}


def _invert_groups(groups: dict[str, tuple[int, ...]]) -> dict[int, str]:
    mapping: dict[int, str] = {}
    for group, codes in groups.items():
        for code in codes:
            if code in mapping:
                raise ValueError(f"Classification code {code} occurs in multiple groups")
            mapping[code] = group
    return mapping


MUNICIPALITY_TO_REGION = {
    f"{code:04d}": region
    for code, region in _invert_groups(MUNICIPALITY_CODES_BY_REGION).items()
}
BUILDING_USE_TO_GROUP = _invert_groups(BUILDING_USE_CODES_BY_GROUP)


def add_documented_classifications(lf: pl.LazyFrame, entity: str) -> pl.LazyFrame:
    """Append non-destructive classifications when their source columns exist."""
    columns = set(lf.collect_schema().names())
    expressions: list[pl.Expr] = []

    if "kommunekode" in columns:
        expressions.append(
            pl.col("kommunekode")
            .replace_strict(
                MUNICIPALITY_TO_REGION,
                default=None,
                return_dtype=pl.String,
            )
            .alias("region_name")
        )

    if entity == "bygning" and "byg021BygningensAnvendelse" in columns:
        expressions.append(
            pl.col("byg021BygningensAnvendelse")
            .replace_strict(
                BUILDING_USE_TO_GROUP,
                default=None,
                return_dtype=pl.String,
            )
            .alias("building_use_group")
        )

    return lf.with_columns(expressions)
