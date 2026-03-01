import os
import json

project_dir = os.path.dirname(os.path.abspath(__file__))
output_file = os.path.join(project_dir, "codigo_projeto.json")

def gather_files():
    data = {}
    for root, dirs, files in os.walk(project_dir):
        if "__pycache__" in root or ".git" in root or ".venv" in root:
            continue
        for file in files:
            # Pega apenas os scripts Python
            if file.endswith(".py"):
                path = os.path.join(root, file)
                rel_path = os.path.relpath(path, project_dir).replace("\\", "/")
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data[rel_path] = f.read()
                except Exception as e:
                    print(f"Skipping {rel_path}: {e}")
    return data

if __name__ == "__main__":
    data = gather_files()
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    print(f"Exportado com sucesso! {len(data)} arquivos salvos em {output_file}")
