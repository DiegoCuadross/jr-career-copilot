"""
Robustness Judge Service
========================
Validador LLM-as-a-Judge que analiza un CV generado para detectar:
  - Alucinaciones (información no respaldada por el perfil real)
  - Inconsistencias (contradicciones internas en el CV)
  - Violaciones éticas (contenido discriminatorio, engañoso o inapropiado)

Usa Google GenAI con Structured Outputs (Pydantic + response_schema).

Uso (desde cv_optimizer.py):
    python cv_optimizer.py --robustness [-c output/optimized_cv.md]

Uso directo:
    python robustness_judge.py [-c output/optimized_cv.md] [-p config/student_profile.yaml]
"""

import os
import sys
import json
import yaml
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional
from enum import Enum

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

load_dotenv()

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

OUTPUT_DIR = Path("output")
REPORT_FILE = OUTPUT_DIR / "robustness_report.json"
MODEL = "gemini-2.5-flash"


# ---------------------------------------------------------------------------
# Modelos Pydantic para Structured Output
# ---------------------------------------------------------------------------

class SeverityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class HallucinationFinding(BaseModel):
    """Afirmación en el CV sin respaldo en el perfil real del candidato."""
    claim: str = Field(description="La afirmación específica encontrada en el CV")
    reason: str = Field(description="Por qué se considera alucinación (no está en el perfil)")
    severity: SeverityLevel = Field(description="Severidad del hallazgo")
    recommendation: str = Field(description="Cómo corregirlo o eliminarlo")


class InconsistencyFinding(BaseModel):
    """Contradicción interna dentro del propio CV."""
    element_a: str = Field(description="Primera afirmación o elemento conflictivo")
    element_b: str = Field(description="Segunda afirmación que contradice a element_a")
    description: str = Field(description="Explicación de la contradicción")
    severity: SeverityLevel = Field(description="Severidad del hallazgo")
    recommendation: str = Field(description="Cómo resolver la inconsistencia")


class EthicalViolation(BaseModel):
    """Contenido discriminatorio, engañoso o inapropiado en el CV."""
    violation_type: str = Field(
        description="Tipo de violación: discrimination | misleading | privacy | bias | other"
    )
    excerpt: str = Field(description="Fragmento del CV donde ocurre la violación")
    description: str = Field(description="Explicación detallada del problema ético")
    severity: SeverityLevel = Field(description="Severidad del hallazgo")
    recommendation: str = Field(description="Cómo corregirlo")


class OverallVerdict(str, Enum):
    PASS = "pass"
    PASS_WITH_WARNINGS = "pass_with_warnings"
    FAIL = "fail"
    CRITICAL_FAIL = "critical_fail"


class RobustnessReport(BaseModel):
    """Reporte completo del análisis de robustez del CV."""
    analysis_timestamp: str = Field(description="Timestamp ISO del análisis")
    candidate_name: str = Field(description="Nombre del candidato analizado")
    cv_source: str = Field(description="Fuente del CV analizado")

    hallucinations: list[HallucinationFinding] = Field(
        default_factory=list,
        description="Lista de alucinaciones detectadas"
    )
    inconsistencies: list[InconsistencyFinding] = Field(
        default_factory=list,
        description="Lista de inconsistencias internas detectadas"
    )
    ethical_violations: list[EthicalViolation] = Field(
        default_factory=list,
        description="Lista de violaciones éticas detectadas"
    )

    hallucination_score: float = Field(
        description="Score 0-10. 10 = sin alucinaciones.", ge=0.0, le=10.0
    )
    consistency_score: float = Field(
        description="Score 0-10. 10 = perfectamente consistente.", ge=0.0, le=10.0
    )
    ethics_score: float = Field(
        description="Score 0-10. 10 = sin violaciones éticas.", ge=0.0, le=10.0
    )
    overall_score: float = Field(
        description="Promedio ponderado: hallucination×0.4 + consistency×0.3 + ethics×0.3",
        ge=0.0, le=10.0
    )

    verdict: OverallVerdict = Field(
        description=(
            "pass (≥8.0) | pass_with_warnings (6.0–7.9) | "
            "fail (4.0–5.9) | critical_fail (<4.0)"
        )
    )
    summary: str = Field(
        description="Resumen ejecutivo del análisis en 3-5 oraciones"
    )
    top_recommendations: list[str] = Field(
        description="Las 3-5 recomendaciones más importantes para mejorar el CV"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("\n[ERROR] La variable de entorno GEMINI_API_KEY no está configurada.")
        print("  1. Crea un archivo '.env' en la raíz del proyecto.")
        print("  2. Agrega: GEMINI_API_KEY=tu_clave_aqui")
        print("  3. Obtén tu clave gratis en: https://aistudio.google.com/app/apikey")
        sys.exit(1)
    return genai.Client(api_key=api_key)


def _profile_to_ground_truth(profile: dict) -> str:
    """Convierte el perfil YAML a texto de referencia (ground truth)."""
    info = profile.get("personal_info", {})
    lines = [
        "=== DATOS VERIFICADOS DEL CANDIDATO (Ground Truth) ===",
        f"Nombre: {info.get('full_name', 'N/A')}",
        f"Email: {info.get('email', 'N/A')}",
        f"Ubicación: {info.get('location', 'N/A')}",
    ]

    if skills := profile.get("skills"):
        lines.append(f"Skills reales: {', '.join(skills)}")

    if summary := profile.get("professional_summary"):
        lines.append(f"Resumen original: {str(summary).strip()}")

    if exp_list := profile.get("experiences"):
        lines.append("Experiencia real:")
        for exp in exp_list:
            lines.append(
                f"  - {exp.get('role')} @ {exp.get('company')} "
                f"({exp.get('start_date', '')}–{exp.get('end_date', '')})"
            )
            for ach in exp.get("achievements", []):
                lines.append(f"      • {ach}")

    if edu_list := profile.get("education"):
        lines.append("Educación real:")
        for edu in edu_list:
            lines.append(
                f"  - {edu.get('degree')} – {edu.get('institution')} "
                f"({edu.get('start_date', '')}–{edu.get('end_date', '')})"
            )
            for ach in edu.get("achievements", []):
                lines.append(f"      • {ach}")

    return "\n".join(lines)


def _build_cv_from_profile(profile: dict) -> str:
    """Genera un CV básico desde el perfil YAML cuando no hay CV externo."""
    info = profile.get("personal_info", {})
    skills = profile.get("skills", [])
    exp_list = profile.get("experiences", [])
    edu_list = profile.get("education", [])

    lines = [
        info.get("full_name", "Candidato"),
        info.get("email", ""),
        info.get("location", ""),
        "",
        "RESUMEN PROFESIONAL",
        str(profile.get("professional_summary", "")).strip(),
        "",
        "HABILIDADES",
        ", ".join(skills),
        "",
        "EXPERIENCIA",
    ]

    for exp in exp_list:
        lines.append(
            f"{exp.get('role')} – {exp.get('company')} "
            f"({exp.get('start_date', '')}–{exp.get('end_date', '')})"
        )
        for ach in exp.get("achievements", []):
            lines.append(f"• {ach}")
        lines.append("")

    lines.append("EDUCACIÓN")
    for edu in edu_list:
        lines.append(
            f"{edu.get('degree')} – {edu.get('institution')} "
            f"({edu.get('start_date', '')}–{edu.get('end_date', '')})"
        )
        for ach in edu.get("achievements", []):
            lines.append(f"• {ach}")

    return "\n".join(lines)


def _build_judge_prompt(ground_truth: str, cv_text: str) -> str:
    return f"""Eres un auditor experto en verificación de CVs y ética profesional.
Tu tarea es analizar un CV para detectar problemas de calidad y ética.

{ground_truth}

=== CV A ANALIZAR ===
{cv_text}

=== INSTRUCCIONES DE ANÁLISIS ===

1. ALUCINACIONES: Identifica afirmaciones en el CV que NO estén respaldadas
   por los datos verificados. Ejemplos:
   - Tecnologías que no aparecen en el perfil real
   - Empresas, títulos o fechas incorrectas
   - Logros específicos sin evidencia en el perfil
   - Certificaciones o premios no listados
   - Niveles de idioma superiores a los registrados

2. INCONSISTENCIAS: Detecta contradicciones dentro del propio CV:
   - Fechas solapadas o incoherentes
   - Habilidades que contradicen la experiencia descrita
   - Cambios de rol sin sentido cronológico
   - Lenguaje contradictorio sobre el mismo rol o logro

3. VIOLACIONES ÉTICAS: Identifica contenido problemático:
   - Información discriminatoria (edad, género, religión, etc.)
   - Exageración fraudulenta de logros o responsabilidades
   - Información privada innecesaria
   - Lenguaje sesgado o inapropiado
   - Reclamaciones de patentes, publicaciones o premios sin base

4. SCORING:
   - hallucination_score: 10 = cero alucinaciones; descuenta por cantidad y severidad
   - consistency_score: 10 = perfectamente consistente
   - ethics_score: 10 = sin violaciones éticas
   - overall_score = hallucination_score×0.4 + consistency_score×0.3 + ethics_score×0.3

5. VEREDICTO:
   - pass: overall_score >= 8.0
   - pass_with_warnings: 6.0 <= overall_score < 8.0
   - fail: 4.0 <= overall_score < 6.0
   - critical_fail: overall_score < 4.0

Sé exhaustivo pero justo. Si el CV es fiel al perfil real, debe recibir puntuación alta.
Devuelve el análisis en el formato estructurado solicitado."""


# ---------------------------------------------------------------------------
# Visualización en consola
# ---------------------------------------------------------------------------

SEVERITY_ICONS = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🔵",
    "info": "⚪",
}

VERDICT_LABELS = {
    "pass": "✅ APROBADO",
    "pass_with_warnings": "⚠️  APROBADO CON ADVERTENCIAS",
    "fail": "❌ REPROBADO",
    "critical_fail": "🚨 FALLO CRÍTICO",
}


def _print_report(report: RobustnessReport) -> None:
    sep = "─" * 60
    print(f"\n{'=' * 60}")
    print(f"  📋 REPORTE DE ROBUSTEZ – {report.candidate_name}")
    print(f"{'=' * 60}")
    print(f"  Fecha  : {report.analysis_timestamp}")
    print(f"  Fuente : {report.cv_source}")
    print(sep)

    print(f"\n  VEREDICTO : {VERDICT_LABELS.get(report.verdict, report.verdict)}")
    print(f"\n  SCORES:")
    print(f"    Alucinaciones  : {report.hallucination_score:.1f} / 10")
    print(f"    Consistencia   : {report.consistency_score:.1f} / 10")
    print(f"    Ética          : {report.ethics_score:.1f} / 10")
    print(f"    GENERAL        : {report.overall_score:.1f} / 10")
    print(f"\n  RESUMEN:\n  {report.summary}")

    if report.hallucinations:
        print(f"\n{sep}")
        print(f"  🧠 ALUCINACIONES ({len(report.hallucinations)}):")
        for i, h in enumerate(report.hallucinations, 1):
            icon = SEVERITY_ICONS.get(h.severity.value if hasattr(h.severity, 'value') else h.severity, "⚪")
            print(f"\n  {i}. {icon} [{str(h.severity).upper()}] {h.claim}")
            print(f"     Razón : {h.reason}")
            print(f"     Fix   : {h.recommendation}")

    if report.inconsistencies:
        print(f"\n{sep}")
        print(f"  🔄 INCONSISTENCIAS ({len(report.inconsistencies)}):")
        for i, inc in enumerate(report.inconsistencies, 1):
            icon = SEVERITY_ICONS.get(inc.severity.value if hasattr(inc.severity, 'value') else inc.severity, "⚪")
            print(f"\n  {i}. {icon} [{str(inc.severity).upper()}] {inc.description}")
            print(f"     A   : {inc.element_a}")
            print(f"     B   : {inc.element_b}")
            print(f"     Fix : {inc.recommendation}")

    if report.ethical_violations:
        print(f"\n{sep}")
        print(f"  ⚖️  VIOLACIONES ÉTICAS ({len(report.ethical_violations)}):")
        for i, ev in enumerate(report.ethical_violations, 1):
            icon = SEVERITY_ICONS.get(ev.severity.value if hasattr(ev.severity, 'value') else ev.severity, "⚪")
            print(f"\n  {i}. {icon} [{str(ev.severity).upper()}] [{ev.violation_type}]")
            print(f"     Fragmento : \"{ev.excerpt}\"")
            print(f"     Problema  : {ev.description}")
            print(f"     Fix       : {ev.recommendation}")

    if report.top_recommendations:
        print(f"\n{sep}")
        print("  💡 TOP RECOMENDACIONES:")
        for i, rec in enumerate(report.top_recommendations, 1):
            print(f"  {i}. {rec}")

    print(f"\n{'=' * 60}\n")


def _save_report(report: RobustnessReport) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    def _serialize(obj):
        if isinstance(obj, Enum):
            return obj.value
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, indent=2, ensure_ascii=False, default=_serialize)

    print(f"✅ Reporte guardado en: {REPORT_FILE}")


# ---------------------------------------------------------------------------
# Ejecución principal
# ---------------------------------------------------------------------------

def run_robustness_check(
    profile: dict,
    cv_path: Optional[str] = None,
) -> RobustnessReport:
    """
    Ejecuta el análisis de robustez LLM-as-a-Judge sobre un CV.

    Args:
        profile: Diccionario del perfil cargado desde YAML.
        cv_path: Ruta al CV generado (opcional). Si no se provee, usa el perfil YAML.

    Returns:
        RobustnessReport con todos los hallazgos y scores.
    """
    cv_source = cv_path if cv_path else "perfil YAML (auto-generado)"

    if cv_path:
        path = Path(cv_path)
        if not path.exists():
            print(f"[ERROR] No se encontró el CV en: {cv_path}")
            sys.exit(1)
        with open(path, "r", encoding="utf-8") as f:
            cv_text = f.read().strip()
        print(f"[INFO] CV cargado desde: {cv_path}")
    else:
        print("[INFO] No se especificó CV externo. Analizando CV generado desde el perfil.")
        cv_text = _build_cv_from_profile(profile)

    ground_truth = _profile_to_ground_truth(profile)
    judge_prompt = _build_judge_prompt(ground_truth, cv_text)

    print(f"\n[INFO] Ejecutando análisis LLM-as-a-Judge con {MODEL}...")
    print("       Detectando: alucinaciones, inconsistencias, violaciones éticas...\n")

    client = _get_client()

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=judge_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RobustnessReport,
                max_output_tokens=8192,
                temperature=0.2,
            ),
        )
    except Exception as exc:
        print(f"\n[ERROR] Falló la llamada a Gemini:\n{exc}")
        sys.exit(1)

    raw_json = response.text
    if not raw_json:
        print("[ERROR] Gemini no devolvió una respuesta válida.")
        sys.exit(1)

    try:
        report_data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        print(f"[ERROR] No se pudo parsear el JSON de respuesta: {exc}")
        print(f"Respuesta (primeros 500 chars):\n{raw_json[:500]}")
        sys.exit(1)

    info = profile.get("personal_info", {})
    report_data["analysis_timestamp"] = datetime.now().isoformat()
    report_data["candidate_name"] = info.get("full_name", "N/A")
    report_data["cv_source"] = cv_source

    report = RobustnessReport(**report_data)
    _print_report(report)
    _save_report(report)
    return report


# ---------------------------------------------------------------------------
# CLI independiente
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validador de robustez de CV con LLM-as-a-Judge."
    )
    parser.add_argument(
        "-c", "--cv", default=None,
        help="Ruta al CV a analizar (.md o .txt). Si no se especifica, usa el perfil YAML."
    )
    parser.add_argument(
        "-p", "--profile", default="config/student_profile.yaml",
        help="Ruta al perfil YAML del candidato."
    )
    return parser.parse_args()


if __name__ == "__main__":
    from file_io import load_profile

    args = _parse_args()
    profile = load_profile(args.profile)
    run_robustness_check(profile, args.cv)
