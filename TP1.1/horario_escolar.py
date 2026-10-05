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
    import time
    from collections import Counter


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


@app.cell
def _(dias, tempos):
    # construir_modelo (variáveis + R1..R7 + buracos de O1)
    def construir_modelo(turmas, disciplinas, salas, excecoes):
        nomes = [d["disciplina"] for d in disciplinas]
        professores = sorted(set(d["professor"] for d in disciplinas))
        modelo = cp_model.CpModel()
 
        # variáveis: x[turma, disciplina, dia, tempo] = 1 se há aula
        x = {}
        for turma in turmas:
            for disc in nomes:
                for dia in dias:
                    for tempo in tempos:
                        x[turma, disc, dia, tempo] = modelo.new_bool_var(
                            f"x_{turma}_{disc}_{dia}_{tempo}")
 
        # R1: uma turma não tem duas aulas ao mesmo tempo
        for turma in turmas:
            for dia in dias:
                for tempo in tempos:
                    modelo.add(sum(x[turma, disc, dia, tempo] for disc in nomes) <= 1)
 
        # R2: carga semanal exata
        for turma in turmas:
            for d in disciplinas:
                modelo.add(
                    sum(x[turma, d["disciplina"], dia, tempo]
                        for dia in dias for tempo in tempos) == d["carga_semanal"])
 
        # R3: no máximo uma aula da disciplina por dia (um bloco de 2, se duplo)
        for turma in turmas:
            for d in disciplinas:
                limite = 2 if d["duplo_periodo"] == "sim" else 1
                for dia in dias:
                    modelo.add(
                        sum(x[turma, d["disciplina"], dia, tempo] for tempo in tempos) <= limite)
 
        # R4: duplo período -> cada tempo com aula tem de ter um vizinho com aula
        for turma in turmas:
            for d in disciplinas:
                for dia in dias:
                    for tempo in tempos:
                        if d["duplo_periodo"] == "sim":
                            modelo.add(
                                x[turma, d["disciplina"], dia, tempo]
                                <= sum(x[turma, d["disciplina"], dia, v]
                                       for v in (tempo - 1, tempo + 1) if v in tempos))
 
        # R5: um professor não dá duas aulas ao mesmo tempo
        for prof in professores:
            for dia in dias:
                for tempo in tempos:
                    modelo.add(
                        sum(x[turma, d["disciplina"], dia, tempo]
                            for turma in turmas for d in disciplinas
                            if d["professor"] == prof) <= 1)
 
        # R6: indisponibilidades dos professores
        for e in excecoes:
            modelo.add(
                sum(x[turma, d["disciplina"], e["dia"], e["periodo"]]
                    for turma in turmas for d in disciplinas
                    if d["professor"] == e["professor"]) == 0)
 
        # R7: capacidade das salas
        for sala in salas:
            if sala["tipo"] == "normal":
                usam = [d for d in disciplinas if d["sala_especial"] == ""]
            else:
                usam = [d for d in disciplinas if d["sala_especial"] == sala["sala"]]
            for dia in dias:
                for tempo in tempos:
                    modelo.add(
                        sum(x[turma, d["disciplina"], dia, tempo]
                            for turma in turmas for d in usam) <= sala["quantidade"])
            
        # O1: buracos. Para cada professor/dia/tempo h:
        #   antes  = há aula em algum tempo <= h
        #   depois = há aula em algum tempo >= h
        #   buraco >= antes + depois - 1 - ocupado   (só é 1 se h está vazio e entre aulas)
        buracos = []
        for prof in professores:
            for dia in dias:
                ocupado = {
                    h: sum(x[turma, d["disciplina"], dia, h]
                           for turma in turmas for d in disciplinas
                           if d["professor"] == prof)
                    for h in tempos
                }
                for h in tempos:
                    antes = modelo.new_bool_var(f"antes_{prof}_{dia}_{h}")
                    depois = modelo.new_bool_var(f"depois_{prof}_{dia}_{h}")
                    buraco = modelo.new_bool_var(f"buraco_{prof}_{dia}_{h}")
                    for k in tempos:
                        if k <= h:
                            modelo.add(antes >= ocupado[k])
                        if k >= h:
                            modelo.add(depois >= ocupado[k])
                    modelo.add(buraco >= antes + depois - 1 - ocupado[h])
                    buracos.append(buraco)
 
        return modelo, x, sum(buracos)

    return (construir_modelo,)


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
def _(construir_modelo, disciplinas, disponibilidade_excecoes, salas, turmas):
    _modelo, _x, _buracos = construir_modelo(turmas, disciplinas, salas, disponibilidade_excecoes)
    _solver = cp_model.CpSolver()
    _estado = _solver.solve(_modelo)
    len(_x), _solver.status_name(_estado)
    return


@app.cell
def _(construir_modelo):
    # Pede ao solver para resolver o modelo e devolve o horário como um conjunto
    # de aulas (turma, disciplina, dia, tempo). Se não houver solução, devolve None.
    def resolver(modelo, x, limite):
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = limite
        estado = solver.solve(modelo)
        nome = solver.status_name(estado)
        if nome in ("OPTIMAL", "FEASIBLE"):
            return nome, {k for k in x if solver.value(x[k]) == 1}
        return nome, None


    # Conta os buracos de um horário olhando só para as aulas, sem usar o solver.
    # Para cada professor e dia: (último tempo - primeiro tempo + 1) - tempos com aula.
    def buracos_totais(horario, disciplinas):
        prof_de = {d["disciplina"]: d["professor"] for d in disciplinas}
        ocupados = {}
        for (turma, disc, dia, tempo) in horario:
            ocupados.setdefault((prof_de[disc], dia), set()).add(tempo)
        return sum((max(ts) - min(ts) + 1) - len(ts) for ts in ocupados.values())


    # Conta as aulas do horário novo que não estavam no antigo.
    def mudancas(antigo, novo):
        return len(novo - antigo)


    # Gera um horário do zero: constrói o modelo e minimiza os buracos (O1).
    def gerar_do_zero(turmas, disciplinas, salas, excecoes, limite=30):
        t0 = time.perf_counter()
        modelo, x, buracos = construir_modelo(turmas, disciplinas, salas, excecoes)
        modelo.minimize(buracos)
        estado, horario = resolver(modelo, x, limite)
        return estado, horario, time.perf_counter() - t0


    # Gera um horário a partir de um anterior: o mesmo modelo, mas com o horário
    # antigo como pista e com o objetivo de manter o máximo de aulas onde estavam.
    def gerar_incremental(anterior, turmas, disciplinas, salas, excecoes, limite=30):
        t0 = time.perf_counter()
        modelo, x, _ = construir_modelo(turmas, disciplinas, salas, excecoes)
        for k in x:
            modelo.add_hint(x[k], 1 if k in anterior else 0)
        modelo.maximize(sum(x[k] for k in anterior if k in x))
        estado, horario = resolver(modelo, x, limite)
        return estado, horario, time.perf_counter() - t0

    return buracos_totais, gerar_do_zero, gerar_incremental, mudancas


@app.cell
def _(
    buracos_totais,
    disciplinas,
    disponibilidade_excecoes,
    gerar_do_zero,
    gerar_incremental,
    mudancas,
    salas,
    turmas,
):
    # Fluxo do R9: gera H0 com os dados iniciais e depois H1 com dados_v2,
    # de duas maneiras (do zero e incremental), para comparar.
    turmas_v2, disciplinas_v2, salas_v2, excecoes_v2 = ler_dados("dados_v2")

    estado_H0, H0, tempo_H0 = gerar_do_zero(
        turmas, disciplinas, salas, disponibilidade_excecoes)
    estado_Z, H1_zero, tempo_Z = gerar_do_zero(
        turmas_v2, disciplinas_v2, salas_v2, excecoes_v2)
    estado_I, H1, tempo_I = gerar_incremental(
        H0, turmas_v2, disciplinas_v2, salas_v2, excecoes_v2)

    mo.md(f"""
    | | estado | tempo (s) | aulas que mudam vs H0 | buracos (O1) |
    |---|---|---|---|---|
    | H0 (`dados/`) | {estado_H0} | {tempo_H0:.3f} | – | {buracos_totais(H0, disciplinas)} |
    | H1 do zero (`dados_v2/`) | {estado_Z} | {tempo_Z:.3f} | {mudancas(H0, H1_zero)} | {buracos_totais(H1_zero, disciplinas_v2)} |
    | H1 incremental (`dados_v2/`) | {estado_I} | {tempo_I:.3f} | {mudancas(H0, H1)} | {buracos_totais(H1, disciplinas_v2)} |
    """)
    return H0, H1, disciplinas_v2, excecoes_v2, salas_v2, turmas_v2


@app.cell
def _(dias, tempos):
    # Confere um horário contra os dados, sem usar o solver.
    # Devolve a lista de violações (vazia = horário válido).
    def verificar(horario, turmas, disciplinas, salas, excecoes):
        erros = []
        info = {d["disciplina"]: d for d in disciplinas}
        prof_de = {d["disciplina"]: d["professor"] for d in disciplinas}

        for (turma, disc, dia, tempo) in horario:
            if turma not in turmas or disc not in info or dia not in dias or tempo not in tempos:
                erros.append(f"Aula inválida: {(turma, disc, dia, tempo)}")
        if erros:
            return erros

        # R1: uma turma não tem duas aulas ao mesmo tempo
        for (turma, dia, tempo), n in Counter((t, di, h) for (t, s, di, h) in horario).items():
            if n > 1:
                erros.append(f"R1: {turma} tem {n} aulas em {dia}, tempo {tempo}")

        # R2: carga semanal exata
        por_disc = Counter((t, s) for (t, s, di, h) in horario)
        for turma in turmas:
            for d in disciplinas:
                n = por_disc[(turma, d["disciplina"])]
                if n != d["carga_semanal"]:
                    erros.append(f"R2: {turma} tem {n} aulas de {d['disciplina']} "
                                 f"(carga {d['carga_semanal']})")

        # R3 e R4: uma aula por dia; no duplo período, um bloco de 2 tempos seguidos
        tempos_do_dia = {}
        for (t, s, di, h) in horario:
            tempos_do_dia.setdefault((t, s, di), []).append(h)
        for (turma, disc, dia), ts in tempos_do_dia.items():
            ts = sorted(ts)
            if info[disc]["duplo_periodo"] == "sim":
                if len(ts) > 2:
                    erros.append(f"R3: {turma} tem {len(ts)} tempos de {disc} em {dia}")
                elif len(ts) == 1 or (len(ts) == 2 and ts[1] - ts[0] != 1):
                    erros.append(f"R4: {turma}, {disc} em {dia} não é um bloco de 2 seguidos: {ts}")
            elif len(ts) > 1:
                erros.append(f"R3: {turma} tem {len(ts)} aulas de {disc} em {dia}")

        # R5: um professor não dá duas aulas ao mesmo tempo
        for (prof, dia, tempo), n in Counter(
                (prof_de[s], di, h) for (t, s, di, h) in horario).items():
            if n > 1:
                erros.append(f"R5: {prof} tem {n} aulas em {dia}, tempo {tempo}")

        # R6: nenhuma aula num tempo em que o professor está indisponível
        for e in excecoes:
            for (t, s, di, h) in horario:
                if prof_de[s] == e["professor"] and di == e["dia"] and h == e["periodo"]:
                    erros.append(f"R6: {e['professor']} tem aula em {di}, tempo {h}, "
                                 f"mas está indisponível")

        # R7: capacidade das salas
        cap_normal = sum(s["quantidade"] for s in salas if s["tipo"] == "normal")
        cap_especial = {s["sala"]: s["quantidade"] for s in salas if s["tipo"] == "especial"}
        uso = Counter()
        for (t, s, di, h) in horario:
            sala = info[s]["sala_especial"] or "normal"
            uso[(sala, di, h)] += 1
        for (sala, dia, tempo), n in uso.items():
            cap = cap_normal if sala == "normal" else cap_especial.get(sala, 0)
            if n > cap:
                erros.append(f"R7: {n} aulas em sala '{sala}' em {dia}, tempo {tempo} (cap. {cap})")

        return erros

    return (verificar,)


@app.cell
def _(
    H0,
    H1,
    disciplinas,
    disciplinas_v2,
    disponibilidade_excecoes,
    excecoes_v2,
    salas,
    salas_v2,
    turmas,
    turmas_v2,
    verificar,
):
    (verificar(H0, turmas, disciplinas, salas, disponibilidade_excecoes),
     verificar(H1, turmas_v2, disciplinas_v2, salas_v2, excecoes_v2))
    return


@app.cell
def _(disciplinas, disponibilidade_excecoes, salas, turmas, verificar):
    # Cada horário abaixo é inválido de propósito. O verificador tem de
    # apanhar a regra certa; se não apanhar, o assert falha.
    _invalidos = {
        "R1": {("7ºA", "Matemática", "Seg", 1), ("7ºA", "Português", "Seg", 1)},
        "R2": set(),
        "R3": {("7ºA", "Matemática", "Seg", 1), ("7ºA", "Matemática", "Seg", 2)},
        "R4": {("7ºA", "Educação Física", "Seg", 4), ("7ºA", "Educação Física", "Seg", 5),
               ("7ºA", "Educação Física", "Ter", 4)},
        "R5": {("7ºA", "História", "Seg", 1), ("7ºB", "Inglês", "Seg", 1)},
        "R6": {("7ºA", "Educação Física", "Seg", 1)},
        "R7": {("7ºA", "Educação Física", "Seg", 4), ("7ºB", "Educação Física", "Seg", 4)},
    }
    for _regra, _h in _invalidos.items():
        _erros = verificar(_h, turmas, disciplinas, salas, disponibilidade_excecoes)
        assert any(e.startswith(_regra) for e in _erros), f"{_regra} não foi detetada"
    "todos os testes passaram"
    return


@app.cell
def _(gerar_do_zero, verificar):
    dados_teste = ler_dados("dados_teste")
    _estado, H_teste, _tempo = gerar_do_zero(*dados_teste)
    (_estado, len(H_teste), verificar(H_teste, *dados_teste))
    return


if __name__ == "__main__":
    app.run()
