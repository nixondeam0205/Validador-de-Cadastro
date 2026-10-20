from __future__ import annotations

import unittest

from input_parser import parse_validation_text
from validation_core import (
    ValidationInputError, copy_text_to_clipboard,
    generate_amazon_validation, generate_meli_validation,
)


def parsed_sample(text="Ana Maria Souza | CPF: 01234567890\nCavalo: ABC1D23"):
    return parse_validation_text(text)


class ValidationCoreTests(unittest.TestCase):
    def controls(self, trailer=False):
        amazon = {key: "OK" for key in ("BRK", "Onboarding", "ET", "TDD", "Checklist", "Placa Cavalo BRK")}
        if trailer:
            amazon["Placa Carreta BRK"] = "OK"
        return {
            "amazon": amazon,
            "fleet": {"apta": True, "values": {}},
            "lweb": {"values": {"Motorista": "Cadastro", "Cavalo": "Cadastro", "Carreta": "Cadastro"}},
            "tractor_year": "2022", "minimum_year": "2013",
        }

    def lookup_rows(self, driver_status="Apto", driver_validity="22/02/2027", vehicle_validity="18/11/2026", trailer_validity=""):
        return [
            {"kind": "motorista", "identifier": "01234567890", "status_brk": driver_status,
             "status": "OK" if driver_status == "Apto" else driver_status,
             "validity": driver_validity, "error": "", "name_from_report": "Ana Maria Souza"},
            {"kind": "veiculo", "identifier": "ABC1D23", "status_brk": "Apto", "status": "OK",
             "validity": vehicle_validity, "error": ""},
            {"kind": "veiculo", "identifier": "DEF2G45", "status_brk": "Apto", "status": "OK",
             "validity": trailer_validity, "error": ""},
        ]

    def test_legacy_amazon_layout_and_date_for_one_driver_and_horse(self):
        result = generate_amazon_validation(parsed_sample(), self.lookup_rows(), self.controls())
        self.assertTrue(result.startswith("🚛 VALIDAÇÃO DE CADASTRO\n\n👤 Motorista:"))
        self.assertIn("012.345.678-90", result)
        self.assertIn("🚛 Placas:\nABC1D23", result)
        self.assertIn("BRK: ✅ OK 22/02/2027", result)
        self.assertIn("Placa Cavalo BRK: ✅ OK 18/11/2026", result)
        self.assertNotIn("RESULTADOS DOS RELATÓRIOS", result)
        self.assertIn("━━━━━━━━━━━━━━━\n🟢 STATUS", result)
        self.assertIn("🟢 FROTA LEGAL", result)
        self.assertIn("🟢 LWEB", result)

    def test_missing_validity_is_not_invented_in_generated_text(self):
        result = generate_amazon_validation(parsed_sample(), self.lookup_rows(driver_validity="", vehicle_validity=""), self.controls())
        self.assertIn("BRK: ✅ OK\n", result)
        self.assertIn("Placa Cavalo BRK: ✅ OK\n", result)
        self.assertNotIn("Validade: Não localizada", result)
        self.assertNotIn("None", result)

    def test_each_driver_and_vehicle_uses_its_own_validity(self):
        parsed = parse_validation_text("Ana Maria Souza | CPF: 01234567890\nBruno Silva Souza | CPF: 12345678901\nCavalo: ABC1D23\nCarreta 1: DEF2G45")
        results = self.lookup_rows()
        results.extend([
            {"kind": "motorista", "identifier": "12345678901", "status_brk": "Vencido", "status": "Vencido", "validity": "06/05/2024", "error": ""},
        ])
        controls = self.controls(trailer=True)
        controls["lweb"]["values"]["Carreta"] = "Cadastro"
        results[2]["validity"] = "18/11/2026"
        text = generate_amazon_validation(parsed, results, controls)
        self.assertIn("BRK: ✅ OK 22/02/2027", text)
        self.assertIn("Motorista 2 BRK: ⚠️ Vencido 06/05/2024", text)
        self.assertIn("Placa Cavalo BRK: ✅ OK 18/11/2026", text)
        self.assertIn("Placa Carreta BRK: ✅ OK", text)

    def test_no_date_and_with_date_keep_legacy_report_structure(self):
        with_date = generate_amazon_validation(parsed_sample(), self.lookup_rows(), self.controls())
        without_date = generate_amazon_validation(parsed_sample(), self.lookup_rows(driver_validity="", vehicle_validity=""), self.controls())
        for required in ("👤 Motorista:", "🚛 Placas:", "FROTA LEGAL", "🟢 LWEB"):
            self.assertIn(required, with_date)
        self.assertIn("BRK: ✅ OK 22/02/2027", with_date)
        self.assertIn("BRK: ✅ OK\n", without_date)

    def test_unknown_report_status_is_not_promoted_to_ok(self):
        rows = self.lookup_rows(driver_status="Pesquisa concluída", driver_validity="")
        rows[0]["status"] = "Pesquisa concluída"
        controls = self.controls()
        controls["amazon"]["BRK"] = "Pesquisa concluída"
        result = generate_amazon_validation(parsed_sample(), rows, controls)
        self.assertIn("BRK: Pesquisa concluída", result)
        self.assertIn("🔴 STATUS", result)

    def test_unlabeled_plate_defaults_to_horse_for_validation(self):
        parsed = parse_validation_text("CPF 01234567890\nABC1D23")
        self.assertEqual(parsed.vehicles[0].role, "Cavalo")

    def test_extra_pasted_phone_is_ignored_in_generated_report(self):
        parsed = parse_validation_text(
            "038.922.934-22\nSERGIO ANICETO DA SILVA\n(81) 97912-4285\nFXT0E66\nDAH8F14"
        )
        text = generate_meli_validation(parsed, {"meli": {}, "meli_use_vecfleet": False})
        self.assertIn("Sergio Aniceto Da Silva | CPF: 038.922.934-22", text)
        self.assertNotIn("97912-4285", text)
        self.assertNotIn("Informações adicionais", text)
        self.assertIn("🚛 Placas:\nFXT0E66 / DAH8F14", text)

    def test_meli_sections_are_generated_without_amazon_report_lookup(self):
        parsed = parse_validation_text("Ana Maria Souza | CPF: 01234567890\nCavalo: ABC1D23\nCarreta 1: DEF2G45")
        meli = {
            ("BRK", "driver:1"): "OK", ("BRK", "vehicle:ABC1D23"): "OK",
            ("BRK", "vehicle:DEF2G45"): "Em análise",
            ("LWEB", "driver:1"): "OK", ("CHECKS", "check:15zenal"): "OK",
        }
        text = generate_meli_validation(parsed, {"meli": meli, "meli_use_vecfleet": False})
        self.assertTrue(text.startswith("🚛 VALIDAÇÃO DE CADASTRO\n\n👤 Motorista:"))
        self.assertIn("🚛 Placas:\nABC1D23 / DEF2G45", text)
        self.assertIn("🔴 BRK", text)
        self.assertIn("GR Carreta 1: ⚠️ Em análise", text)
        self.assertNotIn("VEC FLEET", text)

    def test_meli_empty_sections_are_not_marked_ok(self):
        text = generate_meli_validation(parsed_sample(), {"meli": {}, "meli_use_vecfleet": True})
        self.assertIn("🔴 LWEB", text)
        self.assertIn("🔴 BRK", text)
        self.assertIn("🔴 VEC FLEET", text)
        self.assertIn("🔴 CHECKS", text)

    def test_copy_helper_uses_clipboard_and_does_not_modify_text(self):
        class Clipboard:
            def __init__(self):
                self.value = ""
            def clipboard_clear(self):
                self.value = ""
            def clipboard_append(self, text):
                self.value += text
            def update_idletasks(self):
                pass
        clipboard = Clipboard()
        copy_text_to_clipboard(clipboard, "validação de teste")
        self.assertEqual(clipboard.value, "validação de teste")


if __name__ == "__main__":
    unittest.main()
