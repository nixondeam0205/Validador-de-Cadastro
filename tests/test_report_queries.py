from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import pandas as pd

from input_parser import parse_validation_text
from report_queries import lookup_detected_data, normalize_report_status
from report_store import ReportStore


class ReportQueryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = ReportStore()

    def load_workbook(self, filename, rows):
        path = self.root / filename
        pd.DataFrame(rows).to_excel(path, index=False)
        return path

    def test_queries_each_detected_item_and_returns_raw_status_validity_and_report_name(self):
        self.store.load("motorista", self.load_workbook("drivers.xlsx", [{
            "CPFMotorista": "01234567890", "NomeMotorista": "Nome de teste",
            "EmpresaFaturamento": "AMAZON SERVICOS", "EmpresaSolicitante": "LOSUNG EXPRESS",
            "DhSolicitacao": "01/10/2026 10:00", "StatusPesquisa": "Apto", "DataValidade": "22/02/2027",
        }]))
        self.store.load("veiculo", self.load_workbook("vehicles.xlsx", [{
            "Placa": "ABC1D23", "EmpresaFaturamento": "AMAZON SERVICOS",
            "EmpresaSolicitante": "LOSUNG EXPRESS", "DhSolicitacao": "01/10/2026 10:00",
            "StatusPesquisa": "Repesquisa", "DhValidade": "-",
        }]))
        parsed = parse_validation_text("Nome de teste | CPF: 01234567890\nCavalo: ABC1D23")
        results = lookup_detected_data(self.store, parsed, "AMAZON")
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["status_brk"], "Apto")
        self.assertEqual(results[0]["status"], "OK")
        self.assertEqual(results[0]["validity"], "22/02/2027")
        self.assertEqual(results[0]["name_from_report"], "Nome de teste")
        self.assertEqual(results[1]["status_brk"], "Repesquisa")
        self.assertEqual(results[1]["status"], "Repesquisa")
        self.assertEqual(results[1]["validity"], "")

    def test_research_concluded_is_preserved_and_meli_is_not_queried(self):
        self.assertEqual(normalize_report_status("Pesquisa concluída"), "Pesquisa concluída")
        parsed = parse_validation_text("CPF: 01234567890\nCavalo: ABC1D23")
        results = lookup_detected_data(self.store, parsed, "MELI")
        self.assertTrue(all("critérios de empresa" in item["error"] for item in results))
        self.assertTrue(all("status_brk" not in item or not item["status_brk"] for item in results))


if __name__ == "__main__":
    unittest.main()
