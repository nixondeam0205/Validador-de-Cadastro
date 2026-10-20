from __future__ import annotations

from datetime import datetime
import tkinter as tk
from unittest import TestCase
from unittest.mock import patch

import pandas as pd

from app import ReportImporterApp, RED, GREEN
from report_store import LoadedReport


class AppLayoutTests(TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = ReportImporterApp(self.root)

    def tearDown(self):
        self.root.destroy()

    def install_reports(self):
        driver_data = pd.DataFrame([
            {"CPFMotorista": "01234567890", "NomeMotorista": "Ana Maria Souza", "EmpresaFaturamento": "AMAZON SERVICOS", "EmpresaSolicitante": "LOSUNG EXPRESS", "DhSolicitacao": "2026-10-01", "StatusPesquisa": "Apto", "DataValidade": "22/02/2027"},
            {"CPFMotorista": "12345678901", "NomeMotorista": "Bruno Silva Souza", "EmpresaFaturamento": "AMAZON SERVICOS", "EmpresaSolicitante": "LOSUNG EXPRESS", "DhSolicitacao": "2026-10-02", "StatusPesquisa": "Vencido", "DataValidade": "06/05/2024"},
        ])
        vehicle_data = pd.DataFrame([
            {"Placa": "ABC1D23", "EmpresaFaturamento": "AMAZON SERVICOS", "EmpresaSolicitante": "LOSUNG EXPRESS", "DhSolicitacao": "2026-10-01", "StatusPesquisa": "Apto", "DhValidade": "18/11/2026"},
            {"Placa": "DEF2G45", "EmpresaFaturamento": "AMAZON SERVICOS", "EmpresaSolicitante": "LOSUNG EXPRESS", "DhSolicitacao": "2026-10-01", "StatusPesquisa": "Apto", "DhValidade": "19/12/2026"},
        ])
        now = datetime.now()
        self.app.store.reports["motorista"] = LoadedReport("motorista", driver_data, {
            "cpf": "CPFMotorista", "dh_solicitacao": "DhSolicitacao", "empresa_faturamento": "EmpresaFaturamento",
            "empresa_solicitante": "EmpresaSolicitante", "nome_motorista": "NomeMotorista", "status_pesquisa": "StatusPesquisa", "data_validade": "DataValidade",
        }, "motoristas.xlsx", now)
        self.app.store.reports["veiculo"] = LoadedReport("veiculo", vehicle_data, {
            "placa": "Placa", "dh_solicitacao": "DhSolicitacao", "empresa_faturamento": "EmpresaFaturamento",
            "empresa_solicitante": "EmpresaSolicitante", "status_pesquisa": "StatusPesquisa", "data_validade": "DhValidade",
        }, "veiculos.xlsx", now)

    def test_legacy_aligned_fields_show_individual_report_results_and_dates(self):
        self.install_reports()
        self.app.input_text.insert("1.0", "Ana Maria Souza | CPF: 01234567890\nBruno Silva Souza | CPF: 12345678901\nCavalo: ABC1D23\nCarreta 1: DEF2G45")
        self.app.identify_data()
        self.root.update_idletasks()
        self.assertFalse(hasattr(self.app, "result_tree"))
        self.assertEqual(self.app.amazon_vars["BRK"].get(), "OK")
        self.assertEqual(self.app.amazon_vars["Placa Cavalo BRK"].get(), "OK")
        self.assertEqual(self.app.amazon_vars["Placa Carreta BRK"].get(), "OK")
        self.assertEqual(self.app.validity_labels[("driver1", "")].cget("text"), "22/02/2027")
        self.assertEqual(self.app.validity_labels[("driver1", "")].cget("fg"), GREEN)
        self.assertEqual(self.app.validity_labels[("driver2", "")].cget("text"), "VENCIDO")
        self.assertEqual(self.app.validity_labels[("driver2", "")].cget("fg"), RED)
        self.assertEqual(self.app.validity_labels[("horse", "")].cget("text"), "18/11/2026")
        self.assertEqual(self.app.validity_labels[("trailer", "")].cget("text"), "19/12/2026")

    def test_missing_date_shows_dash_and_meli_does_not_apply_amazon_report_lookup(self):
        self.install_reports()
        self.app.store.reports["motorista"].dataframe.loc[0, "DataValidade"] = "-"
        self.app.input_text.insert("1.0", "Ana Maria Souza | CPF: 01234567890\nCavalo: ABC1D23")
        self.app.identify_data()
        self.assertEqual(self.app.validity_labels[("driver1", "")].cget("text"), "—")
        self.assertEqual(self.app.validity_labels[("driver1", "")].cget("fg"), RED)
        self.app.operation.set("MELI")
        self.app._operation_changed()
        self.assertEqual(self.app.meli_vars[("BRK", "driver:1")].get(), "(SELECIONE)")
        self.assertFalse(self.app.amazon_panel.winfo_manager())
        self.assertEqual(self.app.meli_panel.winfo_manager(), "pack")
        self.app._apply_responsive_scale()
        self.assertFalse(self.app.amazon_panel.winfo_manager())
        self.app.operation.set("AMAZON")
        self.app._operation_changed()
        self.assertEqual(self.app.amazon_panel.winfo_manager(), "pack")

    def test_delete_loaded_data_clears_memory_and_source_file_paths_only(self):
        self.install_reports()
        self.app.paths["motorista"].set("motoristas.xlsx")
        with patch("app.messagebox.askyesno", return_value=True):
            self.app.delete_loaded_data()
        self.assertIsNone(self.app.store.reports["motorista"])
        self.assertIsNone(self.app.store.reports["veiculo"])
        self.assertEqual(self.app.paths["motorista"].get(), "")
        self.assertEqual(self.app.status_widgets["motorista"].cget("text"), "Não carregado")

    def test_trailer_controls_are_present_in_fleet_legal_and_lweb(self):
        self.app._refresh_vehicle_dependent_controls()
        self.assertTrue(self.app.possui_carreta.get())
        self.assertEqual(len(self.app.fleet_fields.grid_slaves(row=2)), 2)
        self.assertEqual(len(self.app.lweb_area.grid_slaves(row=2)), 2)
        self.app.possui_carreta.set(False)
        self.app._trailer_option_changed()
        self.assertEqual(len(self.app.fleet_fields.grid_slaves(row=2)), 0)
        self.assertEqual(len(self.app.lweb_area.grid_slaves(row=2)), 0)
        self.app._apply_responsive_scale()
        self.assertEqual(len(self.app.fleet_fields.grid_slaves(row=2)), 0)
        self.assertEqual(len(self.app.lweb_area.grid_slaves(row=2)), 0)
        self.app.possui_carreta.set(True)
        self.app._trailer_option_changed()
        self.assertEqual(len(self.app.fleet_fields.grid_slaves(row=2)), 2)
        self.assertEqual(len(self.app.lweb_area.grid_slaves(row=2)), 2)

    def test_responsive_window_and_preview_at_target_resolutions(self):
        self.root.deiconify()
        for geometry in ("1920x1080", "1366x768", "1280x720", "1024x600"):
            with self.subTest(geometry=geometry):
                self.root.geometry(geometry)
                self.root.update()
                self.app._apply_responsive_scale()
                self.root.update()
                width, height = (int(part) for part in geometry.split("x"))
                self.assertEqual(self.root.resizable(), (1, 1))
                self.assertEqual(self.root.winfo_width(), width)
                self.assertLessEqual(self.app.canvas.winfo_width(), width)
                self.assertGreaterEqual(self.app.content.winfo_height(), self.app.canvas.winfo_height())
                self.assertTrue(self.app.preview.winfo_ismapped())
                self.app.canvas.yview_moveto(1.0)
                self.root.update()
                self.assertTrue(self.app.preview.winfo_ismapped())

    def test_f1_marks_trailer_status_using_visible_role_selection(self):
        self.app.input_text.insert("1.0", "CPF: 01234567890\nABC1D23\nDEF2G45")
        self.app.identify_data()
        self.app.vehicle_role_vars["DEF2G45"].set("Carreta 2")
        self.app._shortcut_f1()
        self.assertEqual(self.app.amazon_vars["Placa Carreta BRK"].get(), "OK")


if __name__ == "__main__":
    import unittest
    unittest.main()
