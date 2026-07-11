"""Typed column specifications for the temporal BBR CSV entities."""

from __future__ import annotations

from dataclasses import dataclass


COMMON_DATETIME_COLUMNS = frozenset(
    {
        "datafordelerOpdateringstid",
        "registreringFra",
        "registreringTil",
        "virkningFra",
        "virkningTil",
    }
)

COMMON_INTEGER_COLUMNS = frozenset(
    {
        "datafordelerRowVersion",
        "datafordelerRegisterImportSequenceNumber",
    }
)

COMMON_CODE_COLUMNS = frozenset({"forretningsproces", "status"})

COMMON_ID_COLUMNS = frozenset({"datafordelerRowId", "id_lokalId"})


@dataclass(frozen=True)
class EntitySpec:
    """Column typing rules for one BBR entity."""

    name: str
    datetime_columns: frozenset[str] = COMMON_DATETIME_COLUMNS
    integer_columns: frozenset[str] = COMMON_INTEGER_COLUMNS
    code_columns: frozenset[str] = COMMON_CODE_COLUMNS
    id_columns: frozenset[str] = COMMON_ID_COLUMNS
    required_columns: frozenset[str] = frozenset({"id_lokalId"})


BYGNING_SPEC = EntitySpec(
    name="bygning",
    datetime_columns=COMMON_DATETIME_COLUMNS
    | {
        "byg029DatoForMidlertidigOpførtBygning",
        "byg094Revisionsdato",
        "byg112DatoForRegistreringFraStormrådet",
        "byg114DatoForByggeskadeforsikring",
        "byg122Gyldighedsdato",
        "byg127DatoForTilladelseTilUdtræden",
        "byg129DatoForTilladelseTilAlternativBortskaffelseEllerAfledning",
        "byg132DatoForDispensationFritagelseIftKollektivVarmeforsyning",
        "byg140ServitutForUdlejningsEjendomDato",
    },
    integer_columns=COMMON_INTEGER_COLUMNS
    | {
        "byg007Bygningsnummer",
        "byg024AntalLejlighederMedKøkken",
        "byg025AntalLejlighederUdenKøkken",
        "byg026Opførelsesår",
        "byg027OmTilbygningsår",
        "byg038SamletBygningsareal",
        "byg039BygningensSamledeBoligAreal",
        "byg040BygningensSamledeErhvervsAreal",
        "byg041BebyggetAreal",
        "byg042ArealIndbyggetGarage",
        "byg043ArealIndbyggetCarport",
        "byg044ArealIndbyggetUdhus",
        "byg045ArealIndbyggetUdestueEllerLign",
        "byg046SamletArealAfLukkedeOverdækningerPåBygningen",
        "byg047ArealAfAffaldsrumITerrænniveau",
        "byg048AndetAreal",
        "byg049ArealAfOverdækketAreal",
        "byg050ArealÅbneOverdækningerPåBygningenSamlet",
        "byg051Adgangsareal",
        "byg054AntalEtager",
        "byg069Sikringsrumpladser",
        "byg070Fredning",
        "byg111StormrådetsOversvømmelsesSelvrisiko",
        "byg130ArealAfUdvendigEfterisolering",
        "byg150Gulvbelægning",
        "byg151Frihøjde",
        "byg152ÅbenLukketKonstruktion",
        "byg153Konstruktionsforhold",
        "byg301TypeAfFlytning",
        "byg302Tilflytterkommune",
        "byg406Koordinatsystem",
    },
    code_columns=COMMON_CODE_COLUMNS
    | {
        "byg021BygningensAnvendelse",
        "byg030Vandforsyning",
        "byg031Afløbsforhold",
        "byg032YdervæggensMateriale",
        "byg033Tagdækningsmateriale",
        "byg034SupplerendeYdervæggensMateriale",
        "byg035SupplerendeTagdækningsMateriale",
        "byg036AsbestholdigtMateriale",
        "byg037KildeTilBygningensMaterialer",
        "byg052BeregningsprincipCarportAreal",
        "byg053BygningsarealerKilde",
        "byg055AfvigendeEtager",
        "byg056Varmeinstallation",
        "byg057Opvarmningsmiddel",
        "byg058SupplerendeVarme",
        "byg113Byggeskadeforsikringsselskab",
        "byg119Udledningstilladelse",
        "byg121OmfattetAfByggeskadeforsikring",
        "byg123MedlemskabAfSpildevandsforsyning",
        "byg124PåbudVedrSpildevandsafledning",
        "byg126TilladelseTilUdtræden",
        "byg128TilladelseTilAlternativBortskaffelseEllerAfledning",
        "byg131DispensationFritagelseIftKollektivVarmeforsyning",
        "byg134KvalitetAfKoordinatsæt",
        "byg135SupplerendeOplysningOmKoordinatsæt",
        "byg136PlaceringPåSøterritorie",
    },
    id_columns=COMMON_ID_COLUMNS | {"husnummer", "ejerlejlighed", "grund"},
    required_columns=frozenset(
        {
            "id_lokalId",
            "status",
            "forretningsproces",
            "registreringFra",
            "virkningFra",
        }
    ),
)


BBRSAG_SPEC = EntitySpec(
    name="bbrsag",
    datetime_columns=COMMON_DATETIME_COLUMNS
    | {
        "sag002Byggesagsdato",
        "sag003Byggetilladelsesdato",
        "sag004ForventetPåbegyndelsesdato",
        "sag005Påbegyndelsesdato",
        "sag006IbrugtagningsTilladelse",
        "sag007Henlæggelse",
        "sag009ForventetFuldførtDato",
        "sag010FuldførelseAfByggeri",
        "sag013AnmeldelseAfByggearbejde",
        "sag016DelvisIbrugtagningsTilladelse",
        "sag024DatoForModtagelseAfAnsøgningOmByggetilladelse",
        "sag025DatoForFyldestgørendeAnsøgning",
        "sag026DatoForNaboorientering",
        "sag027DatoForFærdigbehandlingAfNaboorientering",
    },
    integer_columns=COMMON_INTEGER_COLUMNS
    | {
        "sag008FærdigtBygningsareal",
        "sag017ForeløbigFærdiggjortBygningsareal",
        "sag018ForeløbigFærdiggjortAntalLejligheder",
        "sag033ForeløbigFærdiggjortAntalLejlighederUdenKøkken",
    },
    code_columns=COMMON_CODE_COLUMNS | {"sag012Byggesagskode", "sag019Bygherreforhold"},
    required_columns=frozenset(
        {
            "id_lokalId",
            "status",
            "sag002Byggesagsdato",
            "sag010FuldførelseAfByggeri",
        }
    ),
)


SAGSNIVEAU_SPEC = EntitySpec(
    name="sagsniveau",
    code_columns=COMMON_CODE_COLUMNS | {"niveautype", "sagstype"},
    id_columns=COMMON_ID_COLUMNS
    | {
        "sagsdataEtage",
        "stamdataEtage",
        "sagsdataEnhed",
        "stamdataEnhed",
        "stamdataBygning",
        "sagsdataBygning",
        "byggesag",
        "sagsdataTekniskAnlæg",
        "stamdataTekniskAnlæg",
        "stamdataOpgang",
        "sagsdataOpgang",
        "stamdataGrund",
        "sagsdataGrund",
    },
    required_columns=frozenset(
        {
            "id_lokalId",
            "status",
            "niveautype",
            "sagstype",
            "byggesag",
        }
    ),
)


ENTITY_SPECS = {
    BYGNING_SPEC.name: BYGNING_SPEC,
    BBRSAG_SPEC.name: BBRSAG_SPEC,
    SAGSNIVEAU_SPEC.name: SAGSNIVEAU_SPEC,
}
