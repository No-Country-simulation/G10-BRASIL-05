"""Script para executar todos os seeders no banco de dados."""
import sys
from app.repositories.database import SessionLocal
from app.seeders.execucao import executar_seeders

def main():
    print("Iniciando execução dos seeders...")
    try:
        with SessionLocal() as db:
            executar_seeders(db)
        print(" Seeders executados com sucesso!")
        print("   - Cidades, categorias e estabelecimentos de saúde semeados.")
        print("   - Médicos e especialidades semeados.")
        print("   - Destinos de roteamento/filas semeados.")
        print("   - Administrador inicial e usuários de teste (diretor, médico, enfermeiro) semeados.")
        print("   - Instância padrão do WhatsApp semeada.")
    except Exception as e:
        print(f" Erro ao executar seeders: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
