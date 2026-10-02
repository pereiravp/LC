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
def _():
    with open("dados/turmas.csv", encoding="utf-8") as f:
        turmas = [linha["turma"] for linha in csv.DictReader(f)]
    turmas
    return (turmas,)


@app.cell(expand_output=True)
def _():
    with open("dados/disciplinas.csv", encoding ="utf-8") as _f:
        disciplinas = [
            {
                "disciplina": linha["disciplina"],
                "professor": linha["professor"],
                "carga_semanal": int(linha["carga_semanal"]),
                "duplo_periodo": linha["duplo_periodo"],
                "sala_especial": linha["sala_especial"],
            }
            for linha in csv.DictReader(_f)
        ]
    disciplinas
    return (disciplinas,)


@app.cell
def _():
    with open("dados/salas.csv", encoding = "utf-8") as _f:
        salas = [
            {
                "sala": linha["sala"],
                "tipo": linha["tipo"],
                "quantidade": int(linha["quantidade"]),
            }
            for linha in csv.DictReader(_f)
        ]
    salas
    return


@app.cell
def _():
    with open("dados/disponibilidade_excecoes.csv", encoding = "utf-8") as _f:
        disponibilidade_excecoes = [
            {
                "professor": linha["professor"],
                "dia": linha["dia"],
                "periodo": int(linha["periodo"]),
            }
            for linha in csv.DictReader(_f)
        ]
    disponibilidade_excecoes
    return


@app.cell
def _(disciplinas):
    dias = ["Seg","Ter","Qua","Qui","Sex"]
    tempos = list(range(1,6))
    nomes_disciplinas = [d["disciplina"] for d in disciplinas]
    professores = sorted(set(p["professor"] for p in disciplinas))

    dias, tempos, nomes_disciplinas, professores
    return dias, nomes_disciplinas, tempos


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
    return


if __name__ == "__main__":
    app.run()
