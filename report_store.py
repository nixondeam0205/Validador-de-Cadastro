"""Importação temporária e seleção determinística de linhas dos relatórios BRK."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
import unicodedata

import pandas as pd


class ReportError(ValueError):
    """Erro seguro e legível relacionado a um relatório ou consulta."""


class ReportNotLoadedError(ReportError):
    pass


class MissingColumnsError(ReportError):
    pass


class AmbiguousRecordError(ReportError):
    pass


ALIASES = {
    "cpf": {"cpf", "cpfmotorista"},
    "placa": {"placa", "placadoveiculo", "placaveiculo"},
    "dh_solicitacao": {
        "dhsolicitacao", "datasolicitacao", "datahorasolicitacao",
        "datasolicitacao pesquisa", "dhsolicitacao pesquisa",
    },
    "empresa_faturamento": {
        "empresafaturamento", "empresadefaturamento", "empresa faturamento",
        "faturamentoempresa",
    },
    "empresa_solicitante": {
        "empresasolicitante", "empresadesolicitacao", "empresasolicitantedapesquisa",
    },
    "nome_motorista": {"nomemotorista"},
    "status_pesquisa": {"statuspesquisa"},
    "data_validade": {"datavalidade", "dhvalidade"},
}

REQUIRED = {
    "motorista": ("cpf", "dh_solicitacao", "empresa_faturamento", "empresa_solicitante"),
    "veiculo": ("placa", "dh_solicitacao", "empresa_faturamento", "empresa_solicitante"),
}

SOURCE_LABELS = {
    "motorista": {
        "cpf": "CPFMotorista",
        "dh_solicitacao": "DhSolicitacao",
        "empresa_faturamento": "EmpresaFaturamento",
        "empresa_solicitante": "EmpresaSolicitante",
    },
    "veiculo": {
        "placa": "Placa",
        "dh_solicitacao": "DhSolicitacao",
        "empresa_faturamento": "EmpresaFaturamento",
        "empresa_solicitante": "EmpresaSolicitante",
    },
}

AMAZON_BILLING_NAMES = {"AMAZON", "AMAZON SERVICOS"}
AMAZON_REQUESTER_NAME = "LOSUNG EXPRESS"


def _header_key(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]", "", text.casefold())


def _text_key(value: object) -> str:
    if pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.upper().split())


def _identifier_key(kind: str, value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value or "")
    if kind == "motorista":
        return re.sub(r"\D", "", text)
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def _cpf_text(value: object) -> object:
    """Keep CPF identifiers textual and restore leading zeros lost by numeric Excel cells."""
    if pd.isna(value):
        return ""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if float(value).is_integer():
            return str(int(value)).zfill(11)
        return str(value)
    text = str(value).strip()
    # Some exports serialize a numeric cell as text ending in .0.
    match = re.fullmatch(r"(\d+)\.0+", text)
    if match:
        return match.group(1).zfill(11)
    return text


def _parse_datetime(value: object):
    if pd.isna(value):
        return pd.NaT
    return pd.to_datetime(value, errors="coerce", dayfirst=True, utc=True)


def _resolve_columns(frame: pd.DataFrame, kind: str) -> dict[str, str]:
    normalized = {}
    for column in frame.columns:
        normalized.setdefault(_header_key(column), []).append(str(column))

    resolved = {}
    missing = []
    required = set(REQUIRED[kind])
    for canonical, aliases in ALIASES.items():
        candidates = []
        accepted = {_header_key(alias) for alias in aliases}
        for alias in accepted:
            candidates.extend(normalized.get(alias, []))
        candidates = list(dict.fromkeys(candidates))
        if not candidates:
            if canonical in required:
                missing.append(SOURCE_LABELS[kind][canonical])
        elif len(candidates) > 1:
            if canonical in required:
                labels = ", ".join(candidates)
                raise MissingColumnsError(
                    f"O relatório contém colunas ambíguas para "
                    f"'{SOURCE_LABELS[kind][canonical]}': {labels}."
                )
        else:
            resolved[canonical] = candidates[0]

    if missing:
        labels = ", ".join(missing)
        available = ", ".join(str(column) for column in frame.columns)
        raise MissingColumnsError(
            f"O relatório de {kind} não contém todas as colunas obrigatórias. "
            f"Faltando (nomes esperados no arquivo): {labels}. "
            f"Colunas encontradas: {available}."
        )
    return resolved


@dataclass
class LoadedReport:
    kind: str
    dataframe: pd.DataFrame
    columns: dict[str, str]
    filename: str
    loaded_at: datetime

    @property
    def record_count(self) -> int:
        return len(self.dataframe.index)


@dataclass
class QuerySelection:
    record: dict
    diagnostics: tuple[str, ...]


class ReportStore:
    """Mantém os dois relatórios e seleções apenas na memória do processo."""

    def __init__(self) -> None:
        self.reports: dict[str, LoadedReport | None] = {"motorista": None, "veiculo": None}
        self.query_results: dict[str, QuerySelection] = {}

    def load(self, kind: str, path: str | Path) -> LoadedReport:
        if kind not in REQUIRED:
            raise ReportError("Tipo de relatório não reconhecido.")
        source = Path(path)
        if source.suffix.casefold() != ".xlsx":
            raise ReportError("Selecione um arquivo Excel .xlsx.")
        try:
            frame = pd.read_excel(source, engine="openpyxl", dtype=object)
        except Exception as exc:
            raise ReportError("Não foi possível ler o arquivo Excel selecionado.") from exc

        # Só substitui o relatório atual após leitura e validação completas.
        columns = _resolve_columns(frame, kind)
        if kind == "motorista":
            cpf_column = columns["cpf"]
            frame[cpf_column] = frame[cpf_column].map(_cpf_text)
        loaded = LoadedReport(kind, frame, columns, source.name, datetime.now())
        self.reports[kind] = loaded
        self.query_results.clear()
        return loaded

    def is_loaded(self, kind: str) -> bool:
        return kind in self.reports and self.reports[kind] is not None

    def select_latest_amazon(self, kind: str, identifier: str) -> QuerySelection:
        report = self.reports.get(kind)
        if report is None:
            raise ReportNotLoadedError("Importe o relatório correspondente antes de consultar.")
        key = _identifier_key(kind, identifier)
        if not key:
            raise ReportError("Informe um CPF ou placa válido para a consulta.")

        identifier_column = report.columns["cpf" if kind == "motorista" else "placa"]
        billing_column = report.columns["empresa_faturamento"]
        date_column = report.columns["dh_solicitacao"]

        selected = report.dataframe.loc[
            report.dataframe[identifier_column].map(lambda value: _identifier_key(kind, value) == key)
        ]
        selected = selected.loc[
            selected[billing_column].map(_text_key).isin(AMAZON_BILLING_NAMES)
        ].copy()
        if selected.empty:
            raise ReportError("Nenhum registro elegível da AMAZON foi encontrado para esse identificador.")

        requester_column = report.columns["empresa_solicitante"]
        selected = selected.loc[
            selected[requester_column].map(_text_key) == AMAZON_REQUESTER_NAME
        ].copy()
        if selected.empty:
            raise ReportError(
                "Há registros faturados para AMAZON, mas nenhum foi solicitado por LOSUNG EXPRESS."
            )

        parsed_dates = selected[date_column].map(_parse_datetime)
        invalid_count = int(parsed_dates.isna().sum())
        valid = selected.loc[~parsed_dates.isna()].copy()
        valid["__parsed_dh_solicitacao__"] = parsed_dates.loc[~parsed_dates.isna()]
        diagnostics = []
        if invalid_count:
            diagnostics.append(f"{invalid_count} registro(s) AMAZON ignorado(s) por DhSolicitacao inválida.")
        if valid.empty:
            raise ReportError(
                "Há registros AMAZON para esse identificador, mas nenhuma data DhSolicitacao válida. "
                "Corrija o relatório e importe-o novamente."
            )

        latest = valid["__parsed_dh_solicitacao__"].max()
        latest_rows = valid.loc[valid["__parsed_dh_solicitacao__"] == latest]
        if len(latest_rows.index) != 1:
            raise AmbiguousRecordError(
                "Há empate entre registros AMAZON na data mais recente; a consulta foi interrompida "
                "para não escolher um registro arbitrariamente."
            )

        row = latest_rows.iloc[0].drop(labels=["__parsed_dh_solicitacao__"])
        record = {str(column): value for column, value in row.items()}
        result = QuerySelection(record, tuple(diagnostics))
        self.query_results[kind] = result
        return result

    def clear(self) -> None:
        self.reports = {"motorista": None, "veiculo": None}
        self.query_results.clear()


__all__ = [
    "AmbiguousRecordError", "LoadedReport", "MissingColumnsError", "QuerySelection",
    "ReportError", "ReportNotLoadedError", "ReportStore",
]
