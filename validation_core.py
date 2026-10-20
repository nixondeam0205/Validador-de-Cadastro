"""Geração pura da prévia para as operações AMAZON e MELI."""

from __future__ import annotations

from typing import Any

from input_parser import ParsedInput, format_cpf
from report_queries import index_results


SELECT = "(SELECIONE)"
STATUS_EMOJI = {
    "OK": "✅ OK", "Renovar": "⚠️ Renovar", "Em análise": "⚠️ Em análise",
    "Inapto": "❌ Inapto", "Vencido": "⚠️ Vencido", "Vencida": "⚠️ Vencida",
    "Sem checklist": "❌ Sem checklist", "Reprovado": "❌ Reprovado",
    "Cadastro": "✅ Cadastro", "Validar": "⚠️ Validar",
    "Atualizar cadastro": "⚠️ Atualizar cadastro", "Sem cadastro": "❌ Sem cadastro",
}
MELI_SECTIONS = ("LWEB", "BRK", "VEC FLEET", "CHECKS")


class ValidationInputError(ValueError):
    pass


def _show_status(value: str) -> str:
    return STATUS_EMOJI.get(value, value)


def _entity_result(result_map: dict, kind: str, identifier: str) -> dict[str, Any] | None:
    key = (kind, identifier)
    if key in result_map:
        return result_map[key]
    return None


def _validation_rows(parsed: ParsedInput):
    if not parsed.drivers:
        raise ValidationInputError("Identifique pelo menos um CPF de motorista antes de gerar a validação.")
    horses = [item for item in parsed.vehicles if item.role == "Cavalo"]
    if len(horses) != 1:
        raise ValidationInputError("Defina exatamente uma das placas identificadas como Cavalo.")
    if any(not item.role for item in parsed.vehicles):
        raise ValidationInputError("Defina se cada placa sem rótulo é Cavalo ou Carreta antes de gerar.")
    return horses[0]


def generate_amazon_validation(parsed: ParsedInput, results: list[dict], controls: dict[str, Any]) -> str:
    horse = _validation_rows(parsed)
    result_map = index_results(results)
    statuses = controls.get("amazon", {})
    fleet = controls.get("fleet", {})
    fleet_apta = bool(fleet.get("apta", False))
    fleet_values = fleet.get("values", {})
    lweb_values = controls.get("lweb", {}).get("values", {})
    detected_trailers = sorted((v for v in parsed.vehicles if v.role.startswith("Carreta")), key=lambda v: v.role)
    has_trailer = bool(controls.get("possui_carreta", bool(detected_trailers)))
    if has_trailer and not detected_trailers:
        raise ValidationInputError("Possui carreta está marcado, mas nenhuma placa foi identificada como Carreta.")
    trailers = detected_trailers if has_trailer else []
    required = ("BRK", "Onboarding", "ET", "TDD", "Checklist", "Placa Cavalo BRK")
    if trailers:
        required += ("Placa Carreta BRK",)
    missing = [key for key in required if statuses.get(key, SELECT) == SELECT]
    if missing:
        raise ValidationInputError("Selecione os status: " + ", ".join(missing) + ".")
    fleet_required = [] if fleet_apta else ["Motorista", "Cavalo"] + (["Carreta"] if trailers else [])
    missing_fleet = [key for key in fleet_required if fleet_values.get(key, SELECT) == SELECT]
    if missing_fleet:
        raise ValidationInputError("Selecione os resultados de Frota Legal: " + ", ".join(missing_fleet) + ".")
    lweb_required = ["Motorista", "Cavalo"] + (["Carreta"] if trailers else [])
    missing_lweb = [key for key in lweb_required if lweb_values.get(key, SELECT) == SELECT]
    if missing_lweb:
        raise ValidationInputError("Selecione os resultados LWEB: " + ", ".join(missing_lweb) + ".")

    driver_results = [_entity_result(result_map, "motorista", d.cpf) or {} for d in parsed.drivers]
    vehicle_results = {v.plate: (_entity_result(result_map, "veiculo", v.plate) or {}) for v in parsed.vehicles}
    def date_suffix(result: dict[str, Any]) -> str:
        value = str(result.get("validity") or "").strip()
        return f" {value}" if value and value not in ("-", "—") else ""

    driver_heading = "👤 Motoristas:" if len(parsed.drivers) > 1 else "👤 Motorista:"
    lines = ["🚛 VALIDAÇÃO DE CADASTRO", "", driver_heading]
    for driver in parsed.drivers:
        lookup = _entity_result(result_map, "motorista", driver.cpf) or {}
        name = driver.name or lookup.get("name_from_report") or "Nome não informado"
        lines.append(f"{name} | CPF: {format_cpf(driver.cpf)}")
    plates = [horse.plate] + [v.plate for v in trailers]
    lines.extend(["", "🚛 Placas:", " / ".join(plates)])

    year = str(controls.get("tractor_year", "")).strip()
    min_year = str(controls.get("minimum_year", "2013"))
    year_ok = year.isdigit() and int(year) >= int(min_year)
    status_ok = all(statuses.get(key) == "OK" for key in required) and year_ok
    status_title = "🟢 STATUS" if status_ok else "🔴 STATUS"
    lines.extend(["", "━━━━━━━━━━━━━━━", status_title])
    lines.append(f"BRK: {_show_status(statuses['BRK'])}{date_suffix(driver_results[0])}")
    if len(driver_results) > 1:
        second_status = driver_results[1].get("status") or driver_results[1].get("status_brk") or "—"
        lines.append(f"Motorista 2 BRK: {_show_status(second_status)}{date_suffix(driver_results[1])}")
    for key in ("Onboarding", "ET", "TDD", "Checklist"):
        lines.append(f"{key}: {_show_status(statuses[key])}")
    horse_result = vehicle_results.get(horse.plate, {})
    lines.append(f"Placa Cavalo BRK: {_show_status(statuses['Placa Cavalo BRK'])}{date_suffix(horse_result)}")
    for trailer in trailers:
        field = "Placa Carreta BRK" if len(trailers) == 1 else f"Placa {trailer.role} BRK"
        line_status = statuses.get(field, statuses.get("Placa Carreta BRK", SELECT))
        lines.append(f"{field}: {_show_status(line_status)}{date_suffix(vehicle_results.get(trailer.plate, {}))}")
    status_year = " ❌ INAPTO" if year and not year_ok else ""
    lines.append(f"Ano do Cavalo: {year}{status_year}")

    lines.extend(["", "━━━━━━━━━━━━━━━", f"{'🟢' if fleet_apta else '🔴'} FROTA LEGAL", f"Inspeção: {'✅ OK' if fleet_apta else '❌ Inapto'}"])
    if not fleet_apta:
        for key in fleet_required:
            lines.append(f"{key}: {_show_status(fleet_values[key])}")
    lweb_ok = all(lweb_values.get(key) == "Cadastro" for key in lweb_required)
    lines.extend(["", "━━━━━━━━━━━━━━━", f"{'🟢' if lweb_ok else '🔴'} LWEB"])
    for key in lweb_required:
        lines.append(f"{key}: {_show_status(lweb_values[key])}")

    if lweb_values.get("Motorista") == "Sem cadastro":
        lines.extend([
            "", "━━━━━━━━━━━━━━━", "📄 DOCUMENTAÇÃO NECESSÁRIA",
            "* CNH em PDF", "* Comprovante de residência",
            "* Certificado de Direção Defensiva (1 ano)", "* CRLV", "* ANTT",
            "* Comprovante bancário do titular da ANTT", "* Chave Pix do titular da ANTT",
            "", "━━━━━━━━━━━━━━━", "📲 CADASTRO",
            "Nosso processo de cadastro é realizado 100% pelo próprio motorista, diretamente pelo aplicativo ou via navegador:",
            "📲 Baixe o aplicativo:",
            "https://play.google.com/store/apps/details?id=br.com.linehaul_driver&pcampaignid=web_share",
            "", "━━━━━━━━━━━━━━━", "📞 SUPORTE",
            "WhatsApp: +55 85 98108-0605", "Ligações: +55 85 99666-0104",
        ])
    return "\n".join(lines)


def _append_lookup(lines: list[str], label: str, identifier: str, result: dict[str, Any] | None) -> None:
    if not result:
        lines.append(f"{label} {identifier}: consulta não realizada.")
        return
    if result.get("error"):
        lines.append(f"{label} {identifier}: {result['error']}")
        return
    raw = result.get("status_brk") or "Status não informado"
    normalized = result.get("status") or "Status não informado"
    validity = result.get("validity") or "Não localizada"
    name = result.get("name_from_report")
    suffix = f" | Nome no relatório: {name}" if name else ""
    requested_at = result.get("requested_at") or "Não localizada"
    billing = result.get("empresa_faturamento") or "—"
    requester = result.get("empresa_solicitante") or "—"
    lines.append(
        f"{label} {identifier}: {raw} → {normalized} | Solicitação: {requested_at} "
        f"| Validade: {validity} | Faturamento: {billing} | Solicitante: {requester}{suffix}"
    )


def generate_meli_validation(parsed: ParsedInput, controls: dict[str, Any]) -> str:
    _validation_rows(parsed)
    detected_trailers = sorted((v for v in parsed.vehicles if v.role.startswith("Carreta")), key=lambda v: v.role)
    has_trailer = bool(controls.get("possui_carreta", bool(detected_trailers)))
    if has_trailer and not detected_trailers:
        raise ValidationInputError("Possui carreta está marcado, mas nenhuma placa foi identificada como Carreta.")
    vehicles = [v for v in parsed.vehicles if v.role == "Cavalo"] + (detected_trailers if has_trailer else [])
    entities = []
    for i, driver in enumerate(parsed.drivers, 1):
        entities.append(("Motorista" if i == 1 else f"Motorista {i}", f"driver:{i}"))
    for vehicle in vehicles:
        entities.append((vehicle.role, f"vehicle:{vehicle.plate}"))
    fields = controls.get("meli", {})
    use_vecfleet = bool(controls.get("meli_use_vecfleet", True))
    sections = ["LWEB", "BRK"] + (["VEC FLEET"] if use_vecfleet else []) + ["CHECKS"]
    lines = ["🚛 VALIDAÇÃO DE CADASTRO", "", "👤 Motoristas:" if len(parsed.drivers) != 1 else "👤 Motorista:"]
    for i, driver in enumerate(parsed.drivers, 1):
        name = driver.name or "Nome não informado"
        lines.append(f"{name} | CPF: {format_cpf(driver.cpf)}")
    lines.extend(["", "🚛 Placas:", " / ".join(v.plate for v in vehicles)])
    for section in sections:
        visible = entities if section != "CHECKS" else [(name, f"check:{name}") for name in ("15zenal", "Anual", "Veicular")]
        values = [fields.get((section, key), SELECT) for _label, key in visible]
        section_ok = bool(values) and all(value == "OK" for value in values)
        lines.extend(["", f"{'🟢' if section_ok else '🔴'} {section}"])
        for label, key in visible:
            value = fields.get((section, key), SELECT)
            if value != SELECT:
                prefix = f"GR {label}" if section == "BRK" else label
                lines.append(f"{prefix}: {_show_status(value)}")
    return "\n".join(lines)


def copy_text_to_clipboard(root: Any, text: str) -> None:
    root.clipboard_clear()
    root.clipboard_append(text)
    root.update_idletasks()


__all__ = [
    "MELI_SECTIONS", "SELECT", "ValidationInputError", "copy_text_to_clipboard",
    "generate_amazon_validation", "generate_meli_validation",
]
