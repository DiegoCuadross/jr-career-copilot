import os
import sys
import argparse
from dotenv import load_dotenv

load_dotenv()

from models import (
    ContactInfo,
    OptimizedExperience,
    OptimizedEducation,
    OptimizedCV
)
from file_io import (
    load_profile,
    load_job_description,
    save_markdown,
    save_html
)
from renderers import (
    HEADERS,
    generate_markdown,
    generate_html
)
from optimizer import optimize_cv


def parse_arguments() -> argparse.Namespace:
    """
    Analiza los argumentos de la línea de comandos.

    Returns:
        argparse.Namespace: Los argumentos analizados por el parser.
    """
    parser = argparse.ArgumentParser(
        description="Optimizador de CV con IA para Ingenieros Junior. "
                    "También incluye simulador de entrevistas y validador de robustez.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Optimizar CV para una vacante
  python cv_optimizer.py -j ../job_description_1.txt

  # Simulador interactivo de entrevista técnica
  python cv_optimizer.py --mock-interview -j ../job_description_1.txt

  # Validar robustez del CV generado
  python cv_optimizer.py --robustness
  python cv_optimizer.py --robustness -c ../output/optimized_cv.md
        """
    )

    # ── Modos de operación (mutuamente excluyentes) ──────────────────────
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--mock-interview",
        action="store_true",
        help="Ejecutar simulador interactivo de entrevista técnica con Gemini como reclutador."
    )
    mode_group.add_argument(
        "--robustness",
        action="store_true",
        help="Ejecutar validador LLM-as-a-Judge que detecta alucinaciones, "
             "inconsistencias y violaciones éticas en el CV."
    )

    # ── Argumentos compartidos ────────────────────────────────────────────
    parser.add_argument(
        "-j", "--job",
        default=None,
        help="Ruta al archivo .txt con la descripción del trabajo/vacante. "
             "Requerido para optimizar el CV y para --mock-interview."
    )
    parser.add_argument(
        "-p", "--profile",
        default="config/student_profile.yaml",
        help="Ruta al perfil YAML del ingeniero junior (default: config/student_profile.yaml)."
    )

    # ── Argumentos del optimizador de CV ─────────────────────────────────
    parser.add_argument(
        "-o", "--output",
        default="output/optimized_cv.md",
        help="Ruta de salida del CV optimizado en Markdown (default: output/optimized_cv.md)."
    )
    parser.add_argument(
        "-l", "--lang",
        default="es",
        choices=["es", "en"],
        help="Idioma de salida: 'es' (español) o 'en' (inglés) (default: 'es')."
    )
    parser.add_argument(
        "-t", "--template",
        default="templates/cv_template.html",
        help="Ruta a la plantilla HTML Jinja2 (default: templates/cv_template.html)."
    )

    # ── Argumento exclusivo del robustness judge ──────────────────────────
    parser.add_argument(
        "-c", "--cv",
        default=None,
        help="Ruta al CV a analizar con --robustness (.md o .txt). "
             "Si no se especifica, genera el CV desde el perfil YAML."
    )

    return parser.parse_args()


def main() -> None:
    """
    Función de ejecución principal del jr-career-copilot.
    Enruta al modo correcto según los flags recibidos.
    """
    args = parse_arguments()

    # ── Modo: Mock Interview ──────────────────────────────────────────────
    if args.mock_interview:
        print("=" * 60)
        print("      MOCK INTERVIEW – jr-career-copilot                  ")
        print("=" * 60)

        if not args.job:
            print("[ERROR] --mock-interview requiere el argumento -j / --job.")
            print("        Ejemplo: python cv_optimizer.py --mock-interview -j ../job_description_1.txt")
            sys.exit(1)

        from mock_interview import run_mock_interview
        profile = load_profile(args.profile)
        job_description = load_job_description(args.job)
        run_mock_interview(profile, job_description, args.job)
        return

    # ── Modo: Robustness Judge ────────────────────────────────────────────
    if args.robustness:
        print("=" * 60)
        print("      ROBUSTNESS JUDGE – jr-career-copilot                ")
        print("=" * 60)

        from robustness_judge import run_robustness_check
        profile = load_profile(args.profile)
        run_robustness_check(profile, args.cv)
        return

    # ── Modo por defecto: Optimizador de CV ──────────────────────────────
    print("=" * 60)
    print("      OPTIMIZADOR DE CV PARA INGENIEROS JUNIOR / TRAINEES   ")
    print("=" * 60)

    if not args.job:
        print("[ERROR] Se requiere el argumento -j / --job para optimizar el CV.")
        print("        Ejemplo: python cv_optimizer.py -j ../job_description_1.txt")
        sys.exit(1)

    print(f"[INFO] Cargando perfil del ingeniero junior desde: '{args.profile}'...")
    profile = load_profile(args.profile)

    print(f"[INFO] Cargando descripción de la oferta laboral en: '{args.job}'...")
    job_description = load_job_description(args.job)

    optimized_cv = optimize_cv(profile, job_description, args.lang)

    print("[INFO] Generando representación en formato Markdown...")
    markdown_content = generate_markdown(optimized_cv, args.lang)

    print("[INFO] Generando representación en formato HTML premium...")
    html_content = generate_html(optimized_cv, args.template, args.lang)

    save_markdown(markdown_content, args.output)

    html_output_path = os.path.splitext(args.output)[0] + ".html"
    save_html(html_content, html_output_path)

    print("=" * 60)
    print("¡Proceso finalizado con éxito! Éxito en tu postulación laboral.")
    print("=" * 60)


if __name__ == "__main__":
    main()