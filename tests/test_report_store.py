from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import pandas as pd

from report_store import (
    AmbiguousRecordError,
    MissingColumnsError,
    ReportError,
    ReportNotLoadedError,
    ReportStore,
)


DRIVER_ROWS = [
    {"CPF": "12345678901", "Empresa de Faturamento": "AMAZON", "Empresa Solicitante": "LOSUNG EXPRESS", "DhSolicitacao": "01/10/2026 09:00"},
    {"CPF": "12345678901", "Empresa de Faturamento": "AMAZON", "Empresa Solicitante": "LOSUNG EXPRESS", "DhSolicitacao": "02/10/2026 10:30"},
    {"CPF": "12345678901", "Empresa de Faturamento": "OUTRA", "Empresa Solicitante": "LOSUNG EXPRESS", "DhSolicitacao": "03/10/2026 12:00"},
]
VEHICLE_ROWS = [
    {"Placa": "ABC1D23", "Empresa de Faturamento": "AMAZON", "Empresa Solicitante": "LOSUNG EXPRESS", "DhSolicitacao": "02/10/2026 10:30"},
]


class ReportStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = ReportStore()

    def workbook(self, filename: str, rows: list[dict]) -> Path:
        path = self.root / filename
        pd.DataFrame(rows).to_excel(path, index=False)
        return path

    def test_loads_both_reports_and_counts_rows(self):
        driver = self.store.load("motorista", self.workbook("motoristas.xlsx", DRIVER_ROWS))
        vehicle = self.store.load("veiculo", self.workbook("veiculos.xlsx", VEHICLE_ROWS))
        self.assertEqual(driver.record_count, 3)
        self.assertEqual(vehicle.record_count, 1)
        self.assertTrue(self.store.is_loaded("motorista"))
        self.assertTrue(self.store.is_loaded("veiculo"))

    def test_loads_brk_export_headers_without_renaming(self):
        driver_rows = [{
            "CPFMotorista": "01234567890", "NomeMotorista": "Nome de teste",
            "EmpresaFaturamento": "AMAZON", "EmpresaSolicitante": "LOSUNG",
            "DhSolicitacao": "02/10/2026 10:30", "StatusPesquisa": "Apto",
            "DataValidade": "22/02/2027",
        }]
        vehicle_rows = [{
            "Placa": "ABC1D23", "EmpresaFaturamento": "AMAZON",
            "EmpresaSolicitante": "LOSUNG", "DhSolicitacao": "02/10/2026 10:30",
            "StatusPesquisa": "Apto", "DhValidade": "22/02/2027",
        }]
        driver = self.store.load("motorista", self.workbook("brk-motorista.xlsx", driver_rows))
        vehicle = self.store.load("veiculo", self.workbook("brk-veiculo.xlsx", vehicle_rows))
        self.assertEqual(driver.record_count, 1)
        self.assertEqual(vehicle.record_count, 1)
        self.assertEqual(driver.columns["cpf"], "CPFMotorista")
        self.assertEqual(driver.columns["nome_motorista"], "NomeMotorista")
        self.assertEqual(driver.columns["status_pesquisa"], "StatusPesquisa")
        self.assertEqual(driver.columns["data_validade"], "DataValidade")
        self.assertEqual(vehicle.columns["placa"], "Placa")
        self.assertEqual(vehicle.columns["data_validade"], "DhValidade")

    def test_numeric_cpf_cell_is_kept_as_eleven_character_text(self):
        rows = [{
            "CPFMotorista": 1234567890,
            "EmpresaFaturamento": "AMAZON",
            "EmpresaSolicitante": "LOSUNG EXPRESS",
            "DhSolicitacao": "02/10/2026 10:30",
        }]
        report = self.store.load("motorista", self.workbook("cpf-numerico.xlsx", rows))
        cpf_value = report.dataframe.iloc[0][report.columns["cpf"]]
        self.assertEqual(cpf_value, "01234567890")
        self.assertIsInstance(cpf_value, str)

    def test_rejects_non_xlsx_and_missing_columns(self):
        csv_path = self.root / "bad.csv"
        csv_path.write_text("CPF\n123\n", encoding="utf-8")
        with self.assertRaises(ReportError):
            self.store.load("motorista", csv_path)
        with self.assertRaises(MissingColumnsError):
            self.store.load("motorista", self.workbook("incomplete.xlsx", [{"CPFMotorista": "123"}]))

    def test_invalid_replacement_keeps_previous_valid_report(self):
        original = self.store.load("motorista", self.workbook("valid.xlsx", DRIVER_ROWS))
        with self.assertRaises(MissingColumnsError):
            self.store.load("motorista", self.workbook("replacement.xlsx", [{"CPF": "999"}]))
        self.assertIs(self.store.reports["motorista"], original)

    def test_successful_replacement_replaces_old_rows(self):
        self.store.load("motorista", self.workbook("first.xlsx", DRIVER_ROWS))
        replacement = [{
            "CPF": "99999999999", "Empresa de Faturamento": "AMAZON",
            "Empresa Solicitante": "LOSUNG EXPRESS", "DhSolicitacao": "04/10/2026 10:00",
        }]
        loaded = self.store.load("motorista", self.workbook("second.xlsx", replacement))
        self.assertEqual(loaded.record_count, 1)
        self.assertEqual(self.store.reports["motorista"].dataframe.iloc[0]["CPF"], "99999999999")

    def test_one_report_can_load_without_the_other(self):
        self.store.load("motorista", self.workbook("motoristas.xlsx", DRIVER_ROWS))
        self.assertTrue(self.store.is_loaded("motorista"))
        self.assertFalse(self.store.is_loaded("veiculo"))

    def test_query_without_report_is_rejected(self):
        with self.assertRaises(ReportNotLoadedError):
            self.store.select_latest_amazon("motorista", "12345678901")

    def test_amazon_precedes_newer_other_company_and_selects_latest_amazon(self):
        self.store.load("motorista", self.workbook("motoristas.xlsx", DRIVER_ROWS))
        selected = self.store.select_latest_amazon("motorista", "123.456.789-01")
        self.assertEqual(selected.record["DhSolicitacao"], "02/10/2026 10:30")
        self.assertEqual(selected.record["Empresa Solicitante"], "LOSUNG EXPRESS")

    def test_amazon_servicos_and_losung_requester_are_required(self):
        rows = [
            {"CPF": "12345678901", "Empresa de Faturamento": "AMAZON SERVICOS", "Empresa Solicitante": "LOSUNG EXPRESS", "DhSolicitacao": "01/10/2026 09:00"},
            {"CPF": "12345678901", "Empresa de Faturamento": "AMAZON SERVICOS", "Empresa Solicitante": "OUTRA OPERAÇÃO", "DhSolicitacao": "03/10/2026 12:00"},
            {"CPF": "12345678901", "Empresa de Faturamento": "MERCADO LIVRE", "Empresa Solicitante": "LOSUNG EXPRESS", "DhSolicitacao": "04/10/2026 12:00"},
        ]
        self.store.load("motorista", self.workbook("amazon-servicos.xlsx", rows))
        selected = self.store.select_latest_amazon("motorista", "12345678901")
        self.assertEqual(selected.record["DhSolicitacao"], "01/10/2026 09:00")
        self.assertEqual(selected.record["Empresa de Faturamento"], "AMAZON SERVICOS")

    def test_does_not_fallback_to_wrong_requester_or_billing_company(self):
        rows = [{
            "CPF": "12345678901", "Empresa de Faturamento": "AMAZON SERVICOS",
            "Empresa Solicitante": "OUTRA OPERAÇÃO", "DhSolicitacao": "01/10/2026 09:00",
        }]
        self.store.load("motorista", self.workbook("other-requester.xlsx", rows))
        with self.assertRaisesRegex(ReportError, "LOSUNG EXPRESS"):
            self.store.select_latest_amazon("motorista", "12345678901")

    def test_tie_at_latest_timestamp_is_reported_not_guessed(self):
        rows = DRIVER_ROWS[:2] + [
            {"CPF": "12345678901", "Empresa de Faturamento": "AMAZON", "Empresa Solicitante": "LOSUNG EXPRESS", "DhSolicitacao": "02/10/2026 10:30"}
        ]
        self.store.load("motorista", self.workbook("motoristas.xlsx", rows))
        with self.assertRaises(AmbiguousRecordError):
            self.store.select_latest_amazon("motorista", "12345678901")

    def test_invalid_dates_are_reported_and_excluded(self):
        rows = [
            {"CPF": "12345678901", "Empresa de Faturamento": "AMAZON", "Empresa Solicitante": "LOSUNG EXPRESS", "DhSolicitacao": "data ruim"},
            DRIVER_ROWS[1],
        ]
        self.store.load("motorista", self.workbook("motoristas.xlsx", rows))
        result = self.store.select_latest_amazon("motorista", "12345678901")
        self.assertEqual(result.record["DhSolicitacao"], DRIVER_ROWS[1]["DhSolicitacao"])
        self.assertTrue(result.diagnostics)

    def test_clear_removes_reports_and_derived_results(self):
        self.store.load("motorista", self.workbook("motoristas.xlsx", DRIVER_ROWS))
        self.store.select_latest_amazon("motorista", "12345678901")
        self.assertTrue(self.store.query_results)
        self.store.clear()
        self.assertFalse(self.store.is_loaded("motorista"))
        self.assertFalse(self.store.query_results)

    def test_import_does_not_create_files_beside_source_workbook(self):
        workbook = self.workbook("motoristas.xlsx", DRIVER_ROWS)
        before = sorted(path.name for path in self.root.iterdir())
        self.store.load("motorista", workbook)
        after = sorted(path.name for path in self.root.iterdir())
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
