"""
Verificação do ambiente para o TP1.1 (Horário Escolar) - Lógica Computacional.

Como correr (na pasta TP1.1, com o ambiente que vais usar no trabalho ativado):
    python check_setup.py

Cada linha imprime [OK] ou [FALHA]. No fim, envia-me o output completo.
"""
import sys
import shutil
import subprocess
from pathlib import Path

resultados = []


def registar(nome, ok, detalhe=""):
    resultados.append(ok)
    estado = "[OK]   " if ok else "[FALHA]"
    print(f"{estado} {nome}" + (f"  ->  {detalhe}" if detalhe else ""))


# 1. Python -------------------------------------------------------------------
v = sys.version_info
registar("Python", v >= (3, 10), f"{v.major}.{v.minor}.{v.micro}  (o cabeçalho do enunciado diz >=3.14, ver nota abaixo)")
if v < (3, 14):
    print("        nota: o cabeçalho '# /// script' dos ficheiros pede Python >=3.14.")
    print("        Só é aplicado se abrires o notebook com 'marimo edit --sandbox' (usa uv).")
    print("        Num ambiente conda/venv normal podes ignorar, ou baixar o valor no TEU ficheiro.")

# 2. Pacotes -------------------------------------------------------------------
def versao_pacote(nome_import, nome_pip=None):
    try:
        mod = __import__(nome_import)
        return True, getattr(mod, "__version__", "?")
    except Exception as e:  # ImportError ou erro de binários
        return False, f"{type(e).__name__}: {e}"


for imp, pip in [("ortools", "ortools"), ("marimo", "marimo"), ("pandas", "pandas")]:
    ok, info = versao_pacote(imp)
    registar(f"Pacote {pip}", ok, info if ok else f"{info}  | instala com: pip install {pip}")

# Pacotes para os TPs seguintes (não bloqueiam o TP1.1)
for imp, pip in [("z3", "z3-solver"), ("cvxpy", "cvxpy")]:
    ok, info = versao_pacote(imp)
    print(f"[info]  {pip} (TPs futuros): {'instalado ' + str(info) if ok else 'não instalado'}")

# 3. Teste funcional do CP-SAT ---------------------------------------------------
try:
    from ortools.sat.python import cp_model

    m = cp_model.CpModel()
    x = m.new_int_var(0, 10, "x")
    y = m.new_int_var(0, 10, "y")
    b = m.new_bool_var("b")
    m.add(x + y == 7)
    m.add(x - y >= 1).only_enforce_if(b)   # restrição condicional (reificação)
    m.add(b == 1)
    m.add_hint(x, 4)                       # 'hint' = ponto de partida (útil no R9)
    m.maximize(x)
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = 10
    estado = s.solve(m)
    ok = estado == cp_model.OPTIMAL and s.value(x) == 7 and s.value(y) == 0
    registar("CP-SAT resolve um modelo de teste", ok,
             f"estado={s.status_name(estado)}, x={s.value(x)}, y={s.value(y)} (esperado OPTIMAL, 7, 0)")
except AttributeError as e:
    registar("CP-SAT resolve um modelo de teste", False,
             f"{e} | versão antiga do ortools? faz: pip install -U ortools")
except Exception as e:
    registar("CP-SAT resolve um modelo de teste", False, f"{type(e).__name__}: {e}")

# 4. Marimo na linha de comandos ---------------------------------------------------
exe = shutil.which("marimo")
if exe:
    try:
        out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=30)
        registar("Comando 'marimo'", out.returncode == 0, out.stdout.strip() or out.stderr.strip())
    except Exception as e:
        registar("Comando 'marimo'", False, str(e))
else:
    registar("Comando 'marimo'", False, "não está no PATH (ambiente ativado? tenta: python -m marimo --version)")

# 5. Git -----------------------------------------------------------------------------
git = shutil.which("git")
if git:
    out = subprocess.run([git, "--version"], capture_output=True, text=True)
    registar("Git", out.returncode == 0, out.stdout.strip())
    nome = subprocess.run([git, "config", "user.name"], capture_output=True, text=True).stdout.strip()
    mail = subprocess.run([git, "config", "user.email"], capture_output=True, text=True).stdout.strip()
    registar("Git configurado (user.name / user.email)", bool(nome and mail),
             f"{nome} <{mail}>" if nome and mail else "faz: git config --global user.name 'O Teu Nome' e user.email")
else:
    registar("Git", False, "não encontrado")

# 6. Ficheiros de dados (e acentos!) ---------------------------------------------------
pasta = Path("dados")
if pasta.exists():
    try:
        import csv
        with open(pasta / "disciplinas.csv", encoding="utf-8", newline="") as f:
            linhas = list(csv.DictReader(f))
        nomes = [l["disciplina"] for l in linhas]
        ok = len(linhas) == 6 and "Matemática" in nomes and "Educação Física" in nomes
        registar("Leitura de dados/disciplinas.csv com acentos (utf-8)", ok, f"{len(linhas)} disciplinas: {nomes}")
    except Exception as e:
        registar("Leitura de dados/disciplinas.csv", False, f"{type(e).__name__}: {e}")
else:
    registar("Pasta dados/", False, "corre este script dentro da pasta TP1.1")

# Resumo -------------------------------------------------------------------------------
print()
print("TUDO PRONTO." if all(resultados) else f"{resultados.count(False)} verificação(ões) falharam - corrige antes de avançar.")
