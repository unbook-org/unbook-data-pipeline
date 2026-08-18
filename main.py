import argparse
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path do Python para evitar erros de importação
sys.path.append(str(Path(__file__).parent))

# Importa o módulo que acabamos de construir
from src.extractors.social.social_parser import run_extraction as parse_social_data

def main():
    parser = argparse.ArgumentParser(description="UnBook 2.0 - Data Pipeline Engine")
    parser.add_argument(
        "--source", 
        choices=["legacy", "sigaa", "social", "all"], 
        default="all", 
        help="Fonte de dados para processar"
    )

    args = parser.parse_args()

    print("🚀 Iniciando UnBook 2.0 Pipeline...")

    if args.source in ["social", "all"]:
        print("\n💬 [SOCIAL SQUAD] Processando dump bruto do Facebook...")
        
        # Chama o parser passando os caminhos corretos (DOM -> Parsed)
        resultados = parse_social_data(
            input_filepath="data/raw/social/facebook_dump_dom.json",
            output_filepath="data/processed/social_parsed.json"
        )
        
        if resultados:
            print(f"✅ Feito! {len(resultados)} posts prontos para o banco de dados!")
        else:
            print("⚠️ Aviso: Nenhum dado gerado. Verifique se o facebook_dump_dom.json existe.")

if __name__ == "__main__":
    main()