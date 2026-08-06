import argparse
import sys
from rich.console import Console
from rich.panel import Panel

console = Console()

def main():
    parser = argparse.ArgumentParser(description="UnBook 2.0 - Data Pipeline CLI")
    parser.add_argument(
        "--source", 
        choices=["legacy", "sigaa", "all"], 
        default="all", 
        help="Fonte dos dados a serem processados (legacy, sigaa, ou all)"
    )
    parser.add_argument(
        "--export", 
        choices=["db", "json", "csv"], 
        default="json", 
        help="Formato de saída dos dados processados"
    )

    args = parser.parse_args()

    console.print(Panel.fit("[bold green]🚀 UnBook 2.0 - Data Pipeline Engine[/bold green]"))

    if args.source in ["legacy", "all"]:
        console.print("📦 [yellow]Iniciando processamento dos dados legados (.txt)...[/yellow]")
        # TODO: Chamar src.extractors.legacy_parser
        console.print("✅ [green]Dados legados processados com sucesso![/green]")

    if args.source in ["sigaa", "all"]:
        console.print("🌐 [yellow]Iniciando Web Scraping do SIGAA/UnB...[/yellow]")
        # TODO: Chamar src.extractors.sigaa_scraper
        console.print("✅ [green]Scraping do SIGAA finalizado![/green]")

    console.print(f"🎉 [bold blue]Pipeline concluída com sucesso! Saída: {args.export}[/bold blue]")

if __name__ == "__main__":
    main()