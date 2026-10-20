"""Identificação conservadora de CPFs, placas e rótulos em texto livre."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
import unicodedata


CPF_PATTERN = re.compile(
    r"(?<!\d)(?:\d{3}[. ]?\d{3}[. ]?\d{3}[- ]?\d{2}|\d{11})(?!\d)"
)
PLATE_PATTERN = re.compile(
    r"(?<![A-Z0-9])(?:[A-Z]{3}[- ]?\d[A-Z]\d{2}|[A-Z]{3}[- ]?\d{4})(?![A-Z0-9])",
    re.IGNORECASE,
)


@dataclass
class DriverInput:
    cpf: str
    name: str = ""
    role: str = ""
    source_line: int = 0


@dataclass
class VehicleInput:
    plate: str
    role: str = ""
    source_line: int = 0


@dataclass
class ParsedInput:
    drivers: list[DriverInput] = field(default_factory=list)
    vehicles: list[VehicleInput] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def normalize_cpf(value: str) -> str:
    return "".join(char for char in value if char.isdigit())


def format_cpf(value: str) -> str:
    digits = normalize_cpf(value)
    if len(digits) != 11:
        return value
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


def normalize_plate(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char)).casefold()


def _clean_name(text: str) -> str:
    text = re.sub(r"^[\s|,:;\-–—]+|[\s|,:;\-–—]+$", "", text)
    text = re.sub(r"^(?:nome\s*(?:do\s+motorista)?|motorista\s*\d*)\s*[:=\-]?\s*", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    if not text or len(text) > 100 or re.search(r"\d", text):
        return ""
    name_pattern = r"[A-Za-zÀ-ÖØ-öø-ÿ]+(?:['’\-][A-Za-zÀ-ÖØ-öø-ÿ]+)*(?:\s+[A-Za-zÀ-ÖØ-öø-ÿ]+(?:['’\-][A-Za-zÀ-ÖØ-öø-ÿ]+)*)+"
    if not re.fullmatch(name_pattern, text):
        return ""
    if _fold(text) in {"motorista", "cpf", "placa", "placas", "dados para validacao"}:
        return ""
    return " ".join(word.capitalize() for word in text.split())


def _name_for_cpf(lines: list[str], line_index: int, match_start: int) -> str:
    line = lines[line_index]
    prefix = line[:match_start]
    prefix = re.sub(r"(?:\|\s*)?CPF\s*[:=]?\s*$", "", prefix, flags=re.I)
    # Prefer an explicit name label on the same line.
    name_label = re.search(r"(?:nome(?:\s+do\s+motorista)?|motorista\s*\d*)\s*[:=]\s*(.+)$", prefix, re.I)
    if name_label:
        return _clean_name(name_label.group(1))
    candidate = _clean_name(prefix)
    if candidate:
        return candidate

    # A standalone name immediately above a CPF is a reasonable association;
    # otherwise the name remains unset rather than being guessed.
    if line_index > 0:
        previous = lines[line_index - 1].strip()
        if previous and not CPF_PATTERN.search(previous) and not PLATE_PATTERN.search(previous):
            candidate = _clean_name(previous)
            if candidate:
                return candidate
    # Some exports paste CPF first and the driver's name on the next line.
    if line_index + 1 < len(lines):
        following = lines[line_index + 1].strip()
        if following and not CPF_PATTERN.search(following) and not PLATE_PATTERN.search(following):
            candidate = _clean_name(following)
            if candidate:
                return candidate
    return ""


def _vehicle_role(line: str, match_start: int) -> str:
    prefix = line[:match_start]
    labels = list(re.finditer(r"\b(cavalo|trator|truck|carreta\s*(\d*))\b", prefix, re.I))
    prior_plates = list(PLATE_PATTERN.finditer(prefix))
    if not labels:
        return ""
    label = labels[-1]
    # A label before an earlier plate on the same line belongs to that earlier
    # plate only; the later one needs its own explicit label.
    if prior_plates and label.start() < prior_plates[-1].end():
        return ""
    if label.group(1).casefold() in ("cavalo", "trator", "truck"):
        return "Cavalo"
    trailer = re.search(r"carreta\s*(\d*)", label.group(1), re.I)
    if trailer:
        return f"Carreta {trailer.group(1) or '1'}"
    return ""


def parse_validation_text(text: str) -> ParsedInput:
    """Parse identifiers in appearance order and associate names/roles only with evidence."""
    lines = text.splitlines()
    result = ParsedInput()
    seen_cpfs: set[str] = set()
    for line_index, line in enumerate(lines):
        for match in CPF_PATTERN.finditer(line):
            cpf = normalize_cpf(match.group(0))
            if len(cpf) != 11 or cpf in seen_cpfs:
                continue
            seen_cpfs.add(cpf)
            ordinal = len(result.drivers) + 1
            name = _name_for_cpf(lines, line_index, match.start())
            result.drivers.append(DriverInput(cpf, name, f"Motorista {ordinal}", line_index + 1))

    # Remove CPF spans first so their digit sequences cannot be mistaken for plates.
    text_without_cpfs = CPF_PATTERN.sub(" ", text.upper())
    clean_lines = text_without_cpfs.splitlines()
    seen_plates: set[str] = set()
    for line_index, line in enumerate(clean_lines):
        for match in PLATE_PATTERN.finditer(line):
            plate = normalize_plate(match.group(0))
            if len(plate) != 7 or plate in seen_plates:
                continue
            seen_plates.add(plate)
            role = _vehicle_role(line, match.start())
            result.vehicles.append(VehicleInput(plate, role, line_index + 1))

    if not result.drivers:
        result.warnings.append("Nenhum CPF de 11 dígitos foi identificado.")
    if not result.vehicles:
        result.warnings.append("Nenhuma placa válida foi identificada.")
    if len(result.drivers) > 2:
        result.warnings.append("Foram encontrados mais de dois CPFs; confira se todos pertencem a esta validação.")
    # Plates arrive in operational order: first tractor, then trailers.
    # Explicit labels remain authoritative; only unlabeled plates get defaults.
    defaults = ("Cavalo", "Carreta 1", "Carreta 2")
    for index, vehicle in enumerate(result.vehicles):
        if not vehicle.role and index < len(defaults):
            vehicle.role = defaults[index]
    if sum(not vehicle.role for vehicle in result.vehicles) > 0:
        result.warnings.append("Defina o papel das placas sem rótulo explícito antes de gerar a validação.")
    if len({vehicle.role for vehicle in result.vehicles if vehicle.role == "Cavalo"}) > 1:
        result.warnings.append("Mais de uma placa foi identificada como Cavalo; revise os papéis.")

    return result


__all__ = [
    "DriverInput", "ParsedInput", "VehicleInput", "format_cpf",
    "normalize_cpf", "normalize_plate", "parse_validation_text",
]
