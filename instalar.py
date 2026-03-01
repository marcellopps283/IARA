import json
import os
import sys

# Nome do arquivo de entrada
JSON_FILE = "codigo_projeto.json"

def main():
    if not os.path.exists(JSON_FILE):
        print(f"❌ Erro crítico: O arquivo '{JSON_FILE}' não foi encontrado nesta pasta.")
        print("Mova o arquivo gerado pelo PC para cá e tente novamente.")
        sys.exit(1)

    print(f"📦 Lendo o projeto do arquivo '{JSON_FILE}'...")
    
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Falha ao ler o JSON: {e}")
        sys.exit(1)

    # Diretório atual onde o script está sendo rodado
    base_dir = os.path.abspath(os.path.dirname(__file__))
    
    count = 0
    os.system("clear" if os.name == "posix" else "cls")
    print("🚀 Iniciando extração dos arquivos do ZeroClaw 2.0...\n")

    for fpath, content in data.items():
        # Impede que o script tente gravar arquivos fora da pasta atual (Segurança contra path traversal)
        abs_path = os.path.abspath(os.path.join(base_dir, fpath))
        if not abs_path.startswith(base_dir):
            print(f"⚠️ Alerta de Segurança: Bloqueada tentativa de escrever fora do diretório base: {fpath}")
            continue

        # Cria as subpastas se elas não existirem (ex: folder skills)
        parent_dir = os.path.dirname(abs_path)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
            print(f"📁 Criada a pasta: {os.path.relpath(parent_dir, base_dir)}")

        # Escreve o conteúdo do arquivo
        try:
            with open(abs_path, "w", encoding="utf-8") as out:
                out.write(content)
            print(f"✅ Arquivo gerado: {fpath}")
            count += 1
        except Exception as e:
            print(f"❌ Erro ao gravar {fpath}: {e}")

    print("\n🎉 ===========================================")
    print(f"✅ Extração Concluída! {count} arquivos restaurados com sucesso.")
    print("O seu ambiente (S21 Ultra, S21 FE ou Moto G4) já está pronto para rodar.")
    print("===========================================\n")

if __name__ == "__main__":
    main()
