import os

# Garante que os testes do backend rodem de forma rápida, offline e determinística
os.environ["OPENROUTER_API_KEY"] = ""
os.environ["GOOGLE_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""
