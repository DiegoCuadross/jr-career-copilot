"""
Mock Interview Service
======================
Simulador interactivo de entrevista técnica con Gemini como reclutador.

Uso (desde src/):
    python cv_optimizer.py --mock-interview -j ../job_description_1.txt

Uso directo:
    python mock_interview.py -j ../job_description_1.txt

Flujo:
    1. Carga el perfil del candidato (config/student_profile.yaml)
    2. Carga la descripción del trabajo (JD)
    3. Gemini actúa como reclutador técnico y hace preguntas contextuales
    4. El candidato responde en la terminal
    5. Gemini da feedback por cada respuesta
    6. Al finalizar (mínimo 4 preguntas), guarda la transcripción en Markdown
"""

import os
import sys
import yaml
import argparse
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

OUTPUT_DIR = Path("output")
TRANSCRIPT_FILE = OUTPUT_DIR / "interview_transcript.md"
MIN_QUESTIONS = 4
MODEL = "gemini-2.5-flash"
END_SIGNAL = "ENTREVISTA_COMPLETADA"


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


def _profile_to_text(profile: dict) -> str:
    """Convierte el perfil YAML a texto estructurado para el prompt."""
    info = profile.get("personal_info", {})
    lines = [
        f"Nombre: {info.get('full_name', 'N/A')}",
        f"Ubicación: {info.get('location', 'N/A')}",
    ]

    if skills := profile.get("skills"):
        lines.append(f"Skills: {', '.join(skills)}")

    if summary := profile.get("professional_summary"):
        lines.append(f"Resumen: {str(summary).strip()}")

    if exp_list := profile.get("experiences"):
        lines.append("Experiencia:")
        for exp in exp_list:
            start = exp.get("start_date", "")
            end = exp.get("end_date", "")
            lines.append(f"  - {exp.get('role')} en {exp.get('company')} ({start}–{end})")
            for ach in exp.get("achievements", []):
                lines.append(f"      • {ach}")

    if edu_list := profile.get("education"):
        lines.append("Educación:")
        for edu in edu_list:
            lines.append(
                f"  - {edu.get('degree')} – {edu.get('institution')} "
                f"({edu.get('start_date', '')}–{edu.get('end_date', '')})"
            )
            for ach in edu.get("achievements", []):
                lines.append(f"      • {ach}")

    return "\n".join(lines)


def _build_system_prompt(profile_text: str, job_description: str) -> str:
    return f"""Eres un reclutador técnico senior de una empresa de tecnología.
Estás entrevistando a un candidato para el siguiente puesto:

=== DESCRIPCIÓN DEL PUESTO ===
{job_description}

=== PERFIL DEL CANDIDATO ===
{profile_text}

=== TU ROL ===
- Conduce una entrevista técnica profesional y realista en ESPAÑOL.
- Haz preguntas técnicas y conductuales relevantes al puesto y al perfil del candidato.
- Las preguntas deben ser específicas: referencia tecnologías concretas del JD y del CV.
- Haz UNA pregunta a la vez. Espera la respuesta antes de continuar.
- Después de cada respuesta da feedback breve (2-3 líneas): qué estuvo bien y qué mejorar.
- Varía los tipos: técnicas, situacionales (STAR), de diseño, de resolución de problemas.
- Haz mínimo {MIN_QUESTIONS} preguntas antes de cerrar la entrevista.
- Cuando hayas terminado escribe exactamente: {END_SIGNAL}
  y luego el resumen/evaluación final del candidato.
- Tono profesional pero amigable. Esta es una simulación educativa.

Empieza con una bienvenida breve y la primera pregunta."""


# ---------------------------------------------------------------------------
# Guardado de transcripción
# ---------------------------------------------------------------------------

def _save_transcript(
    profile: dict,
    jd_path: str,
    conversation: list[dict],
    final_evaluation: str,
) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    info = profile.get("personal_info", {})
    name = info.get("full_name", "Candidato")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        "# Transcripción de Entrevista Mock",
        "",
        f"**Candidato:** {name}  ",
        f"**Job Description:** {jd_path}  ",
        f"**Fecha:** {timestamp}  ",
        "",
        "---",
        "",
    ]

    turn = 0
    for entry in conversation:
        role = entry["role"]
        content = entry["content"]
        if role == "interviewer":
            turn += 1
            lines += [f"### Pregunta {turn}", "", f"**🎙️ Reclutador:**", "", content, ""]
        elif role == "candidate":
            lines += [f"**👤 Candidato:**", "", content, ""]
        elif role == "feedback":
            lines += [f"**💬 Feedback:**", "", content, "", "---", ""]

    lines += [
        "## Evaluación Final",
        "",
        final_evaluation,
        "",
        "---",
        "*Generado por jr-career-copilot – Mock Interview*",
    ]

    with open(TRANSCRIPT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n✅ Transcripción guardada en: {TRANSCRIPT_FILE}")


# ---------------------------------------------------------------------------
# Ejecución principal
# ---------------------------------------------------------------------------

def _sep(char: str = "─", w: int = 60) -> None:
    print(char * w)


def run_mock_interview(profile: dict, job_description: str, jd_path: str) -> None:
    """
    Ejecuta la simulación completa de entrevista interactiva.

    Args:
        profile: Diccionario del perfil cargado desde YAML.
        job_description: Texto del puesto de trabajo.
        jd_path: Ruta del archivo JD (para la transcripción).
    """
    client = _get_client()
    profile_text = _profile_to_text(profile)
    system_prompt = _build_system_prompt(profile_text, job_description)

    chat = client.chats.create(
        model=MODEL,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=8192,
            temperature=0.7,
        ),
    )

    info = profile.get("personal_info", {})
    _sep("=")
    print("  🎙️  MOCK INTERVIEW – jr-career-copilot")
    print(f"  Candidato: {info.get('full_name', 'N/A')}")
    print(f"  Puesto: {Path(jd_path).stem}")
    _sep("=")
    print("\nEscribe tu respuesta y presiona Enter.")
    print("Escribe 'salir' en cualquier momento para terminar.\n")

    conversation: list[dict] = []
    final_evaluation = ""

    # Mensaje inicial — Gemini abre la entrevista
    response = chat.send_message(
        "Comienza la entrevista con una bienvenida breve y la primera pregunta."
    )
    current_output = response.text or ""

    while True:
        # ── ¿Termina aquí? ──────────────────────────────────────────────
        if END_SIGNAL in current_output:
            parts = current_output.split(END_SIGNAL, 1)
            closing = parts[0].strip()
            final_evaluation = parts[1].strip() if len(parts) > 1 else ""

            if closing:
                _sep()
                print(f"\n🎙️  RECLUTADOR:\n\n{closing}\n")
                conversation.append({"role": "interviewer", "content": closing})

            _sep("=")
            print("\n🏁 ENTREVISTA FINALIZADA\n")
            _sep("=")
            print(f"\n📊 EVALUACIÓN FINAL:\n\n{final_evaluation}\n")
            break

        # ── Mostrar pregunta del reclutador ──────────────────────────────
        _sep()
        print(f"\n🎙️  RECLUTADOR:\n\n{current_output}\n")
        conversation.append({"role": "interviewer", "content": current_output})

        # ── Respuesta del candidato ───────────────────────────────────────
        user_input = input("👤 Tu respuesta: ").strip()

        if user_input.lower() in ("salir", "exit", "quit"):
            print("\n[INFO] Entrevista terminada por el usuario.")
            final_evaluation = "La entrevista fue interrumpida por el candidato antes de completarse."
            break

        if not user_input:
            print("[AVISO] Respuesta vacía. Escribe algo para continuar.")
            continue

        conversation.append({"role": "candidate", "content": user_input})
        print("\n⏳ Procesando respuesta...\n")

        next_resp = chat.send_message(user_input)
        full_text = next_resp.text or ""

        # ── ¿Incluye señal de fin en esta respuesta? ─────────────────────
        if END_SIGNAL in full_text:
            parts = full_text.split(END_SIGNAL, 1)
            feedback_and_close = parts[0].strip()
            final_evaluation = parts[1].strip() if len(parts) > 1 else ""

            if feedback_and_close:
                print(f"💬 FEEDBACK:\n{feedback_and_close}\n")
                conversation.append({"role": "feedback", "content": feedback_and_close})

            _sep("=")
            print("\n🏁 ENTREVISTA FINALIZADA\n")
            _sep("=")
            print(f"\n📊 EVALUACIÓN FINAL:\n\n{final_evaluation}\n")
            break
        else:
            # Separar feedback de la siguiente pregunta heurísticamente
            lines = full_text.strip().split("\n")
            feedback_lines, question_lines = [], []
            in_question = False

            question_triggers = (
                "pregunta", "cuéntame", "describe", "explica",
                "¿cómo", "¿qué", "¿puedes", "¿has", "¿cuál",
                "ahora", "siguiente", "pasemos",
            )

            for line in lines:
                lower = line.lower()
                if not in_question and any(t in lower for t in question_triggers):
                    in_question = True
                (question_lines if in_question else feedback_lines).append(line)

            feedback_text = "\n".join(feedback_lines).strip()
            next_question = "\n".join(question_lines).strip() or full_text.strip()

            if feedback_text:
                print(f"💬 FEEDBACK:\n{feedback_text}\n")
                conversation.append({"role": "feedback", "content": feedback_text})

            current_output = next_question

    _save_transcript(profile, jd_path, conversation, final_evaluation)


# ---------------------------------------------------------------------------
# CLI independiente
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulador de entrevista técnica con Gemini."
    )
    parser.add_argument(
        "-j", "--job", required=True,
        help="Ruta al archivo .txt con la descripción del puesto."
    )
    parser.add_argument(
        "-p", "--profile", default="config/student_profile.yaml",
        help="Ruta al perfil YAML del candidato."
    )
    return parser.parse_args()


if __name__ == "__main__":
    from file_io import load_profile, load_job_description

    args = _parse_args()
    profile = load_profile(args.profile)
    jd = load_job_description(args.job)
    run_mock_interview(profile, jd, args.job)
