"""Script auxiliar para limpar o schema public do banco de dados local."""
from sqlalchemy import text
from app.repositories.database import engine

def main():
    print("Conectando ao banco e limpando o schema public...")
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE;"))
        conn.execute(text("CREATE SCHEMA public;"))
    print("Banco limpo com sucesso.")

if __name__ == "__main__":
    main()
