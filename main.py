import sys
import os
import argparse
import webbrowser
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from config import config
from form_parser import GoogleFormParser, GoogleFormData, GoogleSignInRequiredError, QuestionType
from gemini_mapper import GeminiFormMapper
from url_builder import PrefillURLBuilder, QuestionAnswer


if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console()


def print_banner():
    banner = Text(
        "====================================================================\n"
        "             Google Forms AI Job Application Pre-filler            \n"
        "           Intelligent Profile Mapping & 1-Click Review URL         \n"
        "====================================================================",
        style="bold cyan"
    )
    console.print(banner)


def load_profile(profile_path: Path) -> str:
    if not profile_path.exists():
        console.print(f"[bold red]Error:[/bold red] Profile file '{profile_path}' not found!")
        console.print(f"[yellow]Please create or edit '{profile_path}' with your career details.[/yellow]")
        sys.exit(1)
    with open(profile_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def load_job_description(jd_text: Optional[str], jd_file: Optional[str]) -> Optional[str]:
    if jd_text:
        return jd_text.strip()
    if jd_file:
        p = Path(jd_file)
        if not p.exists():
            console.print(f"[bold yellow]Warning:[/bold yellow] Job description file '{jd_file}' not found. Continuing without JD.")
            return None
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    return None


def display_form_overview(form_data: GoogleFormData):
    console.print(Panel(
        f"[bold white]{form_data.title}[/bold white]\n"
        f"[dim]{form_data.description or 'No description provided.'}[/dim]\n\n"
        f"[cyan]Total Questions:[/cyan] {len(form_data.questions)} | "
        f"[green]Fillable Entries:[/green] {len(form_data.fillable_questions)} | "
        f"[yellow]File Uploads:[/yellow] {len(form_data.file_upload_questions)}",
        title="[bold blue]Form Details[/bold blue]",
        border_style="blue"
    ))

    # Alert for resume / file uploads
    file_uploads = form_data.file_upload_questions
    if file_uploads:
        items = "\n".join([f"  * [bold]{q.title}[/bold]" for q in file_uploads])
        console.print(Panel(
            f"[bold yellow][!] File Upload Questions Detected:[/bold yellow]\n{items}\n\n"
            f"[italic]Google Forms deliberately blocks pre-filling file upload fields via URL.\n"
            f"When you open the generated link, all your text answers will be pre-filled, but you must manually attach your resume file before clicking Submit.[/italic]",
            title="[bold yellow]Manual Step Required[/bold yellow]",
            border_style="yellow"
        ))


def display_mapping_table(answers: list[QuestionAnswer]):
    table = Table(title="AI Mapped Answers & Confidence Review", border_style="cyan", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Question Title", style="bold white", width=30)
    table.add_column("AI Selected Answer", style="cyan", width=35)
    table.add_column("Confidence", width=12, justify="center")
    table.add_column("Reasoning", style="dim", width=35)

    for i, ans in enumerate(answers, 1):
        # Format answer display
        if isinstance(ans.answer, list):
            ans_display = ", ".join(ans.answer)
        else:
            ans_display = str(ans.answer)

        if ans.is_other:
            ans_display = f"[Other] {ans_display}"

        # Color-coded confidence
        conf = ans.confidence.upper()
        if conf == "HIGH":
            conf_display = "[bold green]HIGH[/bold green]"
        elif conf == "MEDIUM":
            conf_display = "[bold yellow]MEDIUM[/bold yellow]"
        else:
            conf_display = "[bold red]LOW[/bold red]"

        table.add_row(
            str(i),
            ans.question_title,
            ans_display,
            conf_display,
            ans.reasoning or "-"
        )

    console.print(table)


def run():
    parser = argparse.ArgumentParser(
        description="Google Forms AI Job Application Pre-filler with Gemini"
    )
    parser.add_argument(
        "--url", "-u",
        help="Google Form URL (short 'forms.gle/...' or direct 'docs.google.com/forms/...')"
    )
    parser.add_argument(
        "--jd",
        help="Job Description text"
    )
    parser.add_argument(
        "--jd-file", "-j",
        help="Path to file containing Job Description"
    )
    parser.add_argument(
        "--notes", "-n",
        help="Additional specific notes or instructions for this application"
    )
    parser.add_argument(
        "--profile", "-p",
        default=str(config.DEFAULT_PROFILE_PATH),
        help="Path to Master Profile Markdown (defaults to profile.md)"
    )
    parser.add_argument(
        "--html",
        help="Path to saved form HTML file (use this if the form requires Google sign-in)"
    )
    parser.add_argument(
        "--cookies",
        default=config.GOOGLE_COOKIES,
        help="Google session cookies for fetching sign-in gated forms"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect parsed questions without calling the Gemini API"
    )
    parser.add_argument(
        "--open", "-o",
        dest="open_browser",
        action="store_true",
        default=None,
        help="Automatically open generated URL in your default browser"
    )
    parser.add_argument(
        "--no-open",
        dest="open_browser",
        action="store_false",
        help="Do not open in browser"
    )

    args = parser.parse_args()
    print_banner()

    # Determine form source
    form_url = args.url
    html_file = args.html

    if not form_url and not html_file:
        console.print("[bold yellow]Enter Google Form URL[/bold yellow] (or press Enter to specify an HTML file):")
        form_url = input("> ").strip()
        if not form_url:
            console.print("[bold yellow]Enter path to saved form HTML file:[/bold yellow]")
            html_file = input("> ").strip()

    if not form_url and not html_file:
        console.print("[bold red]Error:[/bold red] You must provide either a Form URL or an HTML file path.")
        sys.exit(1)

    # Parse Form
    form_data: Optional[GoogleFormData] = None
    with console.status("[bold green]Fetching and parsing Google Form structure...[/bold green]"):
        try:
            if html_file:
                console.print(f"[cyan]Reading form from local file:[/cyan] {html_file}")
                form_data = GoogleFormParser.parse_from_file(html_file, base_url=form_url or "")
            else:
                console.print(f"[cyan]Connecting to:[/cyan] {form_url}")
                form_data = GoogleFormParser.parse_from_url(form_url, cookies=args.cookies)
        except GoogleSignInRequiredError as err:
            console.print(Panel(
                f"[bold red]Google Sign-in Required for this Form[/bold red]\n\n"
                f"{err}\n\n"
                f"[bold cyan]Quick Workaround (30 seconds):[/bold cyan]\n"
                f"1. Open the form in your normal browser (where you are logged in).\n"
                f"2. Press [bold]Ctrl + U[/bold] (View Source) or [bold]Ctrl + S[/bold] (Save Page As).\n"
                f"3. Save it as [bold]form.html[/bold] in this folder.\n"
                f"4. Run: [bold green]python main.py --url {form_url} --html form.html[/bold green]",
                title="[bold yellow]Authentication Notice[/bold yellow]",
                border_style="red"
            ))
            sys.exit(1)
        except Exception as e:
            console.print(f"[bold red]Failed to parse form:[/bold red] {e}")
            sys.exit(1)

    # Display form overview
    display_form_overview(form_data)

    fillable_count = len(form_data.fillable_questions)
    if fillable_count == 0:
        console.print("[yellow]No fillable questions found in this form.[/yellow]")
        sys.exit(0)

    # Dry run mode
    if args.dry_run:
        console.print("\n[bold cyan]-- Dry Run Mode: Questions Detected --[/bold cyan]")
        for i, q in enumerate(form_data.questions, 1):
            req_str = "[red]*required[/red]" if q.required else "[dim]optional[/dim]"
            opts = f" | Options: {q.options}" if q.options else ""
            console.print(f"{i}. [bold]{q.title}[/bold] ({q.question_type.value}, entry.{q.entry_id}) {req_str}{opts}")
        sys.exit(0)

    # Load master profile and JD
    profile_content = load_profile(Path(args.profile))
    jd_content = load_job_description(args.jd, args.jd_file)

    if jd_content:
        console.print(f"[green][OK][/green] Loaded Job Description ({len(jd_content)} chars)")
    else:
        console.print("[dim]- No Job Description provided; using Master Profile directly.[/dim]")

    # Call Gemini API
    console.print(f"\n[bold magenta]Mapping questions with Gemini ({config.GEMINI_MODEL})...[/bold magenta]")
    with console.status("[bold magenta]Analyzing requirements and crafting tailored answers...[/bold magenta]"):
        try:
            mapper = GeminiFormMapper()
            answers = mapper.map_form(
                form_data=form_data,
                profile_content=profile_content,
                job_description=jd_content,
                additional_notes=args.notes
            )
        except Exception as e:
            console.print(Panel(
                f"[bold red]Gemini Mapping Failed:[/bold red] {e}\n\n"
                f"Make sure you have set a valid GEMINI_API_KEY in your .env file.\n"
                f"Get a key at: https://aistudio.google.com/",
                border_style="red"
            ))
            sys.exit(1)

    # Display results table
    console.print("")
    display_mapping_table(answers)

    # Build pre-filled URL
    prefilled_url = PrefillURLBuilder.build_url(
        base_url=form_data.url or form_url or "",
        answers=answers
    )

    console.print("\n" + "=" * 70)
    console.print(Panel(
        f"[bold green]Here is your Pre-Filled Review URL:[/bold green]\n\n"
        f"[bold underline cyan]{prefilled_url}[/bold underline cyan]\n\n"
        f"[white]1. Click or open the link above to view your pre-filled Google Form.[/white]\n"
        f"[white]2. Review any items flagged with [bold yellow]MEDIUM[/bold yellow] or [bold red]LOW[/bold red] confidence above.[/white]\n"
        f"[white]3. Attach your resume file (if requested by the employer).[/white]\n"
        f"[white]4. Click [bold green]Submit[/bold green] safely with 100% confidence![/white]",
        title="[bold green]Ready for 1-Click Review[/bold green]",
        border_style="green"
    ))

    # Auto-open browser
    should_open = args.open_browser if args.open_browser is not None else config.AUTO_OPEN_BROWSER
    if should_open:
        console.print("[cyan]Opening pre-filled form in your default browser...[/cyan]")
        webbrowser.open(prefilled_url)
    else:
        console.print("[dim]Auto-open disabled. Copy the URL above and paste it into your browser.[/dim]")


if __name__ == "__main__":
    run()
