from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Define onde o arquivo do banco vai ficar (na raiz do projeto)
DATABASE_URL = "sqlite:///./pesqueiro.db"

# Cria o motor de conexão (Engine)
# check_same_thread=False é necessário apenas para o SQLite
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# Cria a sessão (é o que usaremos para mandar dados pro banco)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Essa é a classe "Mãe" de todas as tabelas
Base = declarative_base()

# Função auxiliar para pegar a conexão em cada requisição
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()