from __future__ import annotations

import unittest

from input_parser import format_cpf, parse_validation_text


class InputParserTests(unittest.TestCase):
    def test_parses_formatted_cpf_and_merco_sul_plate_and_associates_inline_name(self):
        parsed = parse_validation_text("Claudionor Moura De Santiago | CPF: 415.606.123-04\nCavalo: RNQ8F86")
        self.assertEqual(len(parsed.drivers), 1)
        self.assertEqual(parsed.drivers[0].cpf, "41560612304")
        self.assertEqual(parsed.drivers[0].name, "Claudionor Moura De Santiago")
        self.assertEqual(parsed.vehicles[0].plate, "RNQ8F86")
        self.assertEqual(parsed.vehicles[0].role, "Cavalo")
        self.assertEqual(format_cpf(parsed.drivers[0].cpf), "415.606.123-04")

    def test_parses_unformatted_identifiers_and_old_style_plate(self):
        parsed = parse_validation_text("Motorista 1: Ana Maria Souza CPF: 01234567890\nCavalo: RPC-8G32")
        self.assertEqual(parsed.drivers[0].cpf, "01234567890")
        self.assertEqual(parsed.drivers[0].name, "Ana Maria Souza")
        self.assertEqual(parsed.vehicles[0].plate, "RPC8G32")

    def test_parses_two_drivers_and_multiple_labeled_vehicles_in_order(self):
        parsed = parse_validation_text(
            "Motorista 1: Ana Silva | CPF: 01234567890\n"
            "Motorista 2: Beto Souza | CPF: 12345678901\n"
            "Cavalo: ABC1D23\nCarreta 1: DEF2G45\nCarreta 2: GHI3456"
        )
        self.assertEqual([driver.name for driver in parsed.drivers], ["Ana Silva", "Beto Souza"])
        self.assertEqual([vehicle.role for vehicle in parsed.vehicles], ["Cavalo", "Carreta 1", "Carreta 2"])

    def test_same_line_vehicle_labels_are_not_reused_for_the_next_plate(self):
        parsed = parse_validation_text("Cavalo: ABC1D23 / Carreta 1: DEF2G45")
        self.assertEqual([vehicle.role for vehicle in parsed.vehicles], ["Cavalo", "Carreta 1"])

    def test_defaults_unlabeled_plates_to_operational_order(self):
        parsed = parse_validation_text("CPF: 01234567890\nPlacas: ABC1D23 / DEF2G45")
        self.assertEqual([vehicle.role for vehicle in parsed.vehicles], ["Cavalo", "Carreta 1"])
        self.assertFalse(any("papel" in warning for warning in parsed.warnings))

    def test_normalizes_name_ignores_phone_and_defaults_plate_order(self):
        parsed = parse_validation_text(
            "038.922.934-22\nSERGIO ANICETO DA SILVA\n(81) 97912-4285\nFXT0E66\nDAH8F14"
        )
        self.assertEqual(parsed.drivers[0].name, "Sergio Aniceto Da Silva")
        self.assertEqual(parsed.vehicles[0].plate, "FXT0E66")
        self.assertEqual([vehicle.role for vehicle in parsed.vehicles], ["Cavalo", "Carreta 1"])

    def test_duplicate_identifiers_are_deduplicated_and_invalid_cpf_is_ignored(self):
        parsed = parse_validation_text("CPF 01234567890 CPF 01234567890\nCavalo ABC123")
        self.assertEqual(len(parsed.drivers), 1)
        self.assertEqual(len(parsed.vehicles), 0)


if __name__ == "__main__":
    unittest.main()
