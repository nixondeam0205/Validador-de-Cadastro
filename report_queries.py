"""Consulta CPF/placa nos relatórios já carregados, sem chamadas externas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd

from input_parser import ParsedInput, normalize_cpf, normalize_plate
from report_store import ReportError, ReportStore


def _cell_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.strftime("%d/%m/%Y")
    text = str(value).strip()
    return "" if text.casefold() in {"nan", "nat", "none"} else text


def _validity_text(value: Any) -> str:
    text = _cell_text(value)
    return "" if text in {"-", "—"} else text


def normalize_report_status(value: Any) -> str:
    """Normalize only explicitly supported BRK values; preserve every other raw value."""
    raw = _cell_text(value)
    if raw.casefold() == "apto":
        return "OK"
    return raw


def _lookup_one(store: ReportStore, kind: str, identifier: str, operation: str) -> dict[str, Any]:
    base = {"kind": kind, "identifier": identifier, "status_brk": "", "status": "", "validity": "", "error": ""}
    if operation != "AMAZON":
        base["error"] = "Consulta BRK não executada em MELI: os critérios de empresa para essa operação não foram definidos."
        return base
    if not store.is_loaded(kind):
        base["error"] = "Relatório correspondente não carregado."
        return base
    try:
        selection = store.select_latest_amazon(kind, identifier)
    except ReportError as exc:
        base["error"] = str(exc)
        return base

    report = store.reports[kind]
    assert report is not None
    record = selection.record
    status_column = report.columns.get("status_pesquisa")
    validity_column = report.columns.get("data_validade")
    name_column = report.columns.get("nome_motorista") if kind == "motorista" else None
    base.update({
        "record": record,
        "status_brk": _cell_text(record.get(status_column)) if status_column else "",
        "status": normalize_report_status(record.get(status_column)) if status_column else "",
        "validity": _validity_text(record.get(validity_column)) if validity_column else "",
        "requested_at": _cell_text(record.get(report.columns["dh_solicitacao"])),
        "empresa_faturamento": _cell_text(record.get(report.columns["empresa_faturamento"])),
        "empresa_solicitante": _cell_text(record.get(report.columns["empresa_solicitante"])),
        "name_from_report": _cell_text(record.get(name_column)) if name_column else "",
        "diagnostics": selection.diagnostics,
    })
    return base


def lookup_detected_data(store: ReportStore, parsed: ParsedInput, operation: str) -> list[dict[str, Any]]:
    """Return one independent result per identifier; one missing row does not hide others."""
    results: list[dict[str, Any]] = []
    for driver in parsed.drivers:
        row = _lookup_one(store, "motorista", driver.cpf, operation)
        row.update({"role": driver.role, "input_name": driver.name, "display_name": driver.name or row.get("name_from_report", "")})
        results.append(row)
    for vehicle in parsed.vehicles:
        row = _lookup_one(store, "veiculo", vehicle.plate, operation)
        row.update({"role": vehicle.role, "input_name": "", "display_name": ""})
        results.append(row)
    return results


def result_key(kind: str, identifier: str) -> tuple[str, str]:
    return kind, normalize_cpf(identifier) if kind == "motorista" else normalize_plate(identifier)


def index_results(results: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {result_key(item["kind"], item["identifier"]): item for item in results}


__all__ = [
    "index_results", "lookup_detected_data", "normalize_report_status", "result_key",
]
