# /// script
# dependencies = ["marimo"]
# requires-python = ">=3.14"
# ///

import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium")

with app.setup:
    import marimo as mo
    import csv
    from ortools.sat.python import cp_model


@app.cell
def _(disciplinas):
    dias = ["Seg","Ter","Qua","Qui","Sex"]
    tempos = list(range(1,6))
    nomes_disciplinas = [d["disciplina"] for d in disciplinas]
    professores = sorted(set(p["professor"] for p in disciplinas))

    dias, tempos, nomes_disciplinas, professores
    return dias, nomes_disciplinas, professores, tempos


@app.cell
def _(dias, nomes_disciplinas, tempos, turmas):
    modelo = cp_model.CpModel()

    x = {}
    for _turma in turmas:
        for _disc in nomes_disciplinas:
            for _dia in dias:
                for _tempo in tempos:
                    x[_turma,_disc,_dia,_tempo] = modelo.new_bool_var(f"x_{_turma}_{_disc}_{_dia}_{_dia}_{_tempo}")

    len(x)
    return modelo, x


@app.cell
def _(dias, modelo, nomes_disciplinas, tempos, turmas, x):
    # R1. Uma turma não pode ter duas aulas em simultâneo.
    for _turma in  turmas:
        for _dia  in dias:
            for _tempo in tempos:
                modelo.add(sum(x[_turma,_disc,_dia,_tempo] for _disc in nomes_disciplinas) <= 1)
    return


@app.cell
def _(dias, disciplinas, modelo, tempos, turmas, x):
    # R2. Cada disciplina cumpre exatamente a carga semanal definida em disciplinas.csv, para cada turma.

    for _turma in turmas:
        for _d in disciplinas:
            modelo.add(sum(x[_turma,_d["disciplina"],_dia,_tempo] for _dia in dias for _tempo in tempos) == _d["carga_semanal"])
    return


@app.cell
def _(dias, disciplinas, modelo, tempos, turmas, x):
    # R3. No máximo uma aula da mesma disciplina por dia, por turma — exceto disciplinas de duplo período (ver R4), em que o bloco de 2 tempos conta como uma só ocorrência nesse dia.

    for _turma in turmas:
        for _d in disciplinas:
            _limite = 2 if _d["duplo_periodo"] == "sim" else 1
            for _dia in dias:
                modelo.add(sum(x[_turma,_d["disciplina"],_dia,_tempo] for _tempo in tempos) <= _limite)
    return


@app.cell
def _(dias, disciplinas, modelo, tempos, turmas, x):
    # R4. Disciplinas marcadas duplo_periodo=sim só podem ser dadas em blocos de 2 tempos consecutivos, no mesmo dia (nunca um tempo isolado).

    for _turma in turmas:
        for _d in disciplinas:
            for _dia in dias:
                for _tempo in tempos:
                    if _d["duplo_periodo"] == "sim":
                        modelo.add(x[_turma, _d["disciplina"], _dia, _tempo] 
                                   <= sum( x[_turma, _d["disciplina"], _dia, _v] for _v in (_tempo - 1, _tempo + 1) if _v in tempos))
    return


@app.cell
def _(dias, disciplinas, modelo, professores, tempos, turmas, x):
    # R5. Um professor não pode dar duas aulas em simultâneo, mesmo que sejam a turmas ou disciplinas diferentes.

    for _prof in professores:
        for _dia in dias:
            for _tempo in tempos:
                modelo.add(sum(x[_turma, _d["disciplina"],_dia,_tempo] for _turma in turmas for _d in disciplinas if _d["professor"] == _prof) <= 1)
    return


@app.cell
def _(disciplinas, disponibilidade_excecoes, modelo, turmas, x):
    # R6. Um professor só pode dar aulas nos tempos em que está disponível (disponibilidade_excecoes.csv).

    for _excecao in disponibilidade_excecoes:
        modelo.add(sum(x[_turma, _d["disciplina"],_excecao["dia"],_excecao["periodo"]] for _turma in turmas for _d in disciplinas if _excecao["professor"] == _d["professor"]) == 0)
    return


@app.cell
def _(dias, disciplinas, modelo, salas, tempos, turmas, x):
    # R7. Cada aula ocupa uma sala. Disciplinas com sala_especial só podem usar salas desse tipo; as restantes usam salas normal. Em nenhum tempo o número de aulas a decorrer num tipo de sala pode exceder a quantidade desse tipo definida em salas.csv.

    for _sala in salas:
        if _sala["tipo"] == "normal":
            _usam = [_d for _d in disciplinas if _d["sala_especial"] == ""]  
        else:
            _usam = [_d for _d in disciplinas if _d["sala_especial"] == _sala["sala"]]
        for _dia in dias:
            for _tempo in tempos:
                modelo.add(sum(x[_turma,_d["disciplina"],_dia,_tempo] for _turma in turmas for _d in _usam) <= _sala["quantidade"])
    return


@app.function
# R8. Os dados de entrada são sempre lidos dos ficheiros CSV — ver secção anterior — nunca escritos diretamente no código.

def ler_dados(pasta):
    with open(f"{pasta}/turmas.csv", encoding="utf-8") as f:
        turmas = [linha["turma"] for linha in csv.DictReader(f)]
    with open(f"{pasta}/disciplinas.csv", encoding="utf-8") as f:
        disciplinas = [
            {
                "disciplina": linha["disciplina"],
                "professor": linha["professor"],
                "carga_semanal": int(linha["carga_semanal"]),
                "duplo_periodo": linha["duplo_periodo"],
                "sala_especial": linha["sala_especial"],
            }
            for linha in csv.DictReader(f)
        ]
    with open(f"{pasta}/salas.csv", encoding="utf-8") as f:
        salas = [
            {
                "sala": linha["sala"],
                "tipo": linha["tipo"],
                "quantidade": int(linha["quantidade"]),
            }
            for linha in csv.DictReader(f)
        ]
    with open(f"{pasta}/disponibilidade_excecoes.csv", encoding="utf-8") as f:
        disponibilidade_excecoes = [
            {
                "professor": linha["professor"],
                "dia": linha["dia"],
                "periodo": int(linha["periodo"]),
            }
            for linha in csv.DictReader(f)
        ]

    return turmas, disciplinas, salas, disponibilidade_excecoes


@app.cell
def _():
    turmas, disciplinas, salas, disponibilidade_excecoes = ler_dados("dados")
    return disciplinas, disponibilidade_excecoes, salas, turmas


@app.cell
def _():
    _t, _di, _s, _ex = ler_dados("dados_v2")
    _ex
    return


@app.cell
def _():
    # R9. O teu notebook tem de suportar o seguinte fluxo: (horario_escolar_enunciado.py)

    return


@app.cell
def _():
    # O1. Minimizar o número total de "buracos" no horário de cada professor — um buraco é um tempo livre, no meio do dia, entre a primeira e a última aula desse professor nesse dia.
    return


@app.cell
def _(modelo):
    solver = cp_model.CpSolver()
    estado = solver.solve(modelo)
    solver.status_name(estado)
    return


if __name__ == "__main__":
    app.run()
