import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import inspect
    import os
    import subprocess
    import sys
    import textwrap
    import time
    from pathlib import Path

    import marimo as mo
    import numpy as np

    import cvp as C
    import test_cvp as T

    # O Exercício 2 pede o solver Clarabel. A variável de ambiente CVP_SOLVER=scipy
    # existe só para correr o notebook numa máquina sem cvxpy.
    SOLVER = os.environ.get("CVP_SOLVER", "clarabel")

    def codigo(*objetos):
        """Mostra o código-fonte de funções como bloco de código."""
        fonte = "\n\n".join(textwrap.dedent(inspect.getsource(o)).rstrip() for o in objetos)
        return mo.md("```python\n" + fonte + "\n```")

    def tabela(cabecalho, linhas):
        """Tabela em Markdown a partir de uma lista de linhas."""
        cab = "| " + " | ".join(cabecalho) + " |"
        sep = "|" + "|".join("---" for _ in cabecalho) + "|"
        corpo = ["| " + " | ".join(str(c) for c in linha) + " |" for linha in linhas]
        return "\n".join([cab, sep] + corpo)

    return C, Path, SOLVER, T, codigo, mo, np, subprocess, sys, tabela, time


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # TP2 · Exercício 2: o problema do vetor mais próximo (CVP) com programação cónica

    `cvxpy` com o solver Clarabel e um branch-and-bound próprio

    Lógica Computacional 2026/27 · Licenciatura em Ciências da Computação · Universidade do Minho

    Grupo 21: Gonçalo Pereira (111783) e David Mimoso (111115)

    ---

    ## Resumo

    Dado um reticulado em $\mathbb{R}^m$ e um ponto $t$, queremos o ponto do reticulado mais próximo de $t$, com os
    coeficientes inteiros limitados a $0\le z_i\le\ell$. Se se deixarem os $z_i$ serem reais, o problema é um problema
    cónico de segunda ordem (SOCP) e o Clarabel resolve-o. Como o Clarabel não trata variáveis inteiras, os inteiros são
    tratados por um algoritmo de *branch-and-bound* escrito por nós, que resolve uma relaxação cónica em cada nó. O resultado
    é comparado com dois métodos exatos que não usam relaxações (força bruta e enumeração por esfera).

    ## Correspondência com o enunciado
    """)
    return


@app.cell(hide_code=True)
def _(mo, tabela):
    mo.md(tabela(
        ["Enunciado", "O que se pede", "Onde está"],
        [
            ["Ex. 2", "Problema de otimização cónica resolvido com a interface `cvxpy` e o solver `Clarabel`", "§2"],
            ["Ex. 2", "O Clarabel não trata inteiros: codificar um algoritmo de relaxação (por exemplo, branch-and-bound)", "§3"],
            ["Ex. 2", "Verificar que os $g_i$ formam mesmo uma base; $g_{i,j}\\in[0,1]$ aleatórios", "§1.3"],
            ["Ex. 2", "Limite $0\\le z_i\\le\\ell$; alvo $t=G^\\top u$ com $u\\in[0,\\ell]$ uniforme", "§1.3"],
            ["Ex. 2", "Casos $k=30,40,50$, $m\\sim2k$ e $\\ell\\in\\{1,5\\}$", "§4.2"],
            ["Regras gerais", "Descrição do problema e da abordagem; código; testes de correção, eficiência e escala", "§1 a §5"],
            ["Regras gerais", "Diálogo com ferramentas LLM", "§7"],
            ["Extras", "O enunciado não tem secção de extras. Incluem-se uma poda barata e a comparação de regras de ramificação (§3.3, §5.2), limites inferior e superior quando o tempo acaba (§4.2) e dois verificadores exatos independentes (§4.1, §5.1)", "§3 a §5"],
        ],
    ))
    return


@app.cell(hide_code=True)
def _(SOLVER, mo):
    mo.callout(mo.md(
        "O código está em `cvp.py` e os testes em `test_cvp.py`; o notebook mostra os excertos relevantes junto da explicação "
        "e todas as tabelas são calculadas quando o notebook corre. O solver usado nas relaxações é "
        f"{SOLVER}. O `Mosek` não foi usado porque exige licença de estudante."), kind="info")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ## 1. O problema

    ### 1.1 O que se quer calcular
    Os vetores $g_1,\dots,g_k\in\mathbb{R}^m$ formam uma base. O reticulado é o conjunto das combinações lineares com
    coeficientes inteiros, $x=\sum_i z_i\,g_i$. No enunciado só se admitem coeficientes $0\le z_i\le\ell$. Dado o alvo
    $t\in\mathbb{R}^m_+$, o CVP pede
    $$\min_{z\in\{0,\dots,\ell\}^k}\ \Big\|\sum_{i=1}^k z_i\,g_i-t\Big\|_2 \;=\; \min_{z}\ \|A z-t\|_2,$$
    onde $A$ é a matriz $m\times k$ cujas colunas são os $g_i$ (ou seja, $A=G^\top$ se $G$ tiver os $g_i$ nas linhas).

    ### 1.2 Um exemplo pequeno
    Com $k=3$, $m=6$ e $\ell=1$ há só $2^3=8$ pontos admissíveis, e podemos ver todos. O alvo é $t=G^\top u$ com $u$ real
    em $[0,1]^3$, por isso o alvo, em geral, não é ele próprio um ponto do reticulado.
    """)
    return


@app.cell
def _(C, mo, np, tabela):
    import itertools as _it
    _inst = C.gerar_instancia(3, 6, 1, semente=2)
    _pontos = []
    for _z in _it.product(range(2), repeat=3):
        _pontos.append((C.distancia(_inst, _z), _z))
    _pontos.sort()
    _linhas = [[str(list(z)), f"{d:.4f}", "mais próximo" if i == 0 else ""] for i, (d, z) in enumerate(_pontos)]
    _G = "\n".join("  " + "  ".join(f"{v:.2f}" for v in r) for r in _inst.G)
    mo.md(
        f"Base $G$ (uma linha por vetor):\n\n```text\n{_G}\n```\n\n"
        f"Alvo $t=G^\\top u$ com $u=({', '.join(f'{v:.3f}' for v in _inst.u)})$:\n\n"
        f"`t = {np.array2string(_inst.t, precision=3)}`\n\n"
        + tabela(["z", "distância a t", ""], _linhas)
        + f"\n\nO ponto mais próximo é $z={list(_pontos[0][1])}$. Arredondar $u$ coordenada a coordenada daria "
          f"$z={[int(v) for v in np.round(_inst.u)]}$, que {'é o mesmo ponto' if tuple(int(v) for v in np.round(_inst.u)) == _pontos[0][1] else 'não é o melhor'}. "
          "Com $k$ grande, arredondar nem sempre dá o melhor ponto, "
          "e o número de candidatos, $(\\ell+1)^k$, torna impossível testá-los todos."
    )
    return


@app.cell(hide_code=True)
def _(C, codigo, mo):
    _texto = mo.md(r"""
    ### 1.3 Geração das instâncias e verificação da base

    Seguem-se as regras do enunciado:

    * $G$ tem entradas uniformes em $[0,1]$ (são probabilidades), com $m=2k$;
    * é preciso verificar que os $g_i$ são linearmente independentes: isso acontece sse o menor valor singular de $G$ é
      positivo (equivalentemente, $G$ tem característica $k$). Se não fosse, gerava-se outra matriz;
    * $u$ é uniforme em $[0,\ell]^k$ e $t=G^\top u$, que tem todas as componentes positivas.

    A semente fixa a instância, para que os resultados se possam repetir.
    """)
    mo.vstack([_texto, codigo(C.Instancia, C.verificar_base, C.gerar_instancia)])
    return


@app.cell(hide_code=True)
def _(C, mo, np, tabela):
    _linhas = []
    for _k in (30, 40, 50):
        for _l in (1, 5):
            _i = C.gerar_instancia(_k, 2 * _k, _l, semente=1)
            _linhas.append([_k, _i.m, _l, np.linalg.matrix_rank(_i.G), f"{_i.sigma_min:.3f}",
                            f"{_i.G.min():.3f} a {_i.G.max():.3f}", f"{_i.t.min():.2f}"])
    mo.md(
        "Instâncias do enunciado (semente 1). A característica é igual a $k$ em todas, logo os $g_i$ formam uma base:\n\n"
        + tabela(["k", "m", "ℓ", "característica de G", "menor valor singular", "entradas de G", "menor componente de t"], _linhas)
    )
    return


@app.cell(hide_code=True)
def _(C, codigo, mo):
    _texto = mo.md(r"""
    ---
    ## 2. O modelo cónico com `cvxpy`

    ### 2.1 Relaxação
    Se os $z_i$ forem reais em vez de inteiros, o problema fica
    $$\min_{z\in\mathbb{R}^k}\ \|A z-t\|_2\quad\text{s.a.}\quad 0\le z\le \ell,$$
    que é equivalente a $\min s$ com $\|Az-t\|_2\le s$ (uma restrição de cone de segunda ordem) e as restrições lineares
    $0\le z\le\ell$. É um SOCP, que o Clarabel resolve. O valor ótimo é um limite inferior da distância inteira, porque
    todo o ponto inteiro admissível também é admissível na relaxação.

    No branch-and-bound há variáveis já fixas num valor inteiro; a relaxação de cada nó só tem como incógnitas as
    variáveis livres e o alvo é ajustado ao que as fixas contribuem, $t'=t-A_{\text{fixas}}\,z_{\text{fixas}}$.
    Código com `cvxpy`:
    """)
    mo.vstack([_texto, codigo(C._relaxar_clarabel)])
    return


@app.cell(hide_code=True)
def _(C, SOLVER, mo, np, tabela, time):
    _l, _k = 5, 30
    _inst = C.gerar_instancia(_k, 2 * _k, _l, semente=1)
    _linhas = []
    for _nome in ([SOLVER] + (["scipy"] if SOLVER != "scipy" else [])):
        _t0 = time.perf_counter()
        _d, _x = C.RELAXACOES[_nome](_inst.A, _inst.t, _l, np.zeros(_k, bool), np.zeros(_k))
        _linhas.append([_nome, f"{_d:.2e}", f"{np.abs(_x - _inst.u).max():.2e}", f"{time.perf_counter() - _t0:.3f}"])
    mo.md(
        f"### 2.2 A relaxação na raiz (instância $k={_k}$, $m={2*_k}$, $\\ell={_l}$)\n\n"
        + tabela(["resolvedor", "distância ótima", "erro máximo em z", "tempo (s)"], _linhas)
        + "\n\nComo $t=G^\\top u$ com $u$ dentro da caixa, a relaxação tem solução exata $z=u$ e distância 0. "
          "Isso mostra duas coisas: o solver está a resolver o problema certo e, por outro lado, a relaxação na raiz não diz "
          "nada sobre a distância inteira, pois dá limite inferior 0. Todo o trabalho está em ir fixando variáveis. "
          + ("A linha `scipy` é um resolvedor de apoio (mínimos quadrados com limites) que serve para conferir o Clarabel."
             if SOLVER != "scipy" else "")
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ## 3. O branch-and-bound

    ### 3.1 Algoritmo
    O Clarabel não trata variáveis inteiras, por isso o tratamento dos inteiros é feito por um algoritmo de relaxação.
    Cada nó da árvore é um conjunto de variáveis já fixas em valores inteiros, e tem associado o valor da relaxação,
    que é um limite inferior para todas as soluções inteiras que o completam.

    1. Raiz. Resolve-se a relaxação sem nada fixo. Arredonda-se o seu ótimo e melhora-se esse ponto (§3.2); fica como melhor solução
       conhecida, com distância $U$ (limite superior).
    2. Escolha do nó. Tira-se da lista o nó com menor limite inferior $L$ (*best-first*). Se $L\ge U$, nenhum nó restante pode
       melhorar e a solução é ótima.
    3. Ramificação. Escolhe-se uma variável livre $z_i$ e criam-se $\ell+1$ filhos, um por cada valor $a\in\{0,\dots,\ell\}$ para $z_i$.
    4. Cada filho. Se a poda barata (§3.3) já mostra que não pode melhorar $U$, é descartado. Senão, resolve-se a relaxação do filho:
       se o seu valor é $\ge U$ é podado; senão, arredonda-se, melhora-se o ponto, atualiza-se $U$ se for caso disso, e o filho entra na lista.

    A variável escolhida é, de forma aproximada, a que mais faz subir a distância ao ser arredondada. Se $d_i$ for a distância
    da coluna $g_i$ ao subespaço gerado pelas outras colunas livres, fixar $z_i$ no inteiro mais próximo do valor $z_i^{*}$ da
    relaxação faz a distância subir cerca de $|z_i^{*}-\text{round}(z_i^{*})|\,d_i$ (exatamente isso se os limites $0\le z\le\ell$
    não estivessem ativos). Escolhe-se o $i$ com maior valor desta quantidade. É só um critério para a árvore ficar pequena:
    qualquer escolha dá o mesmo ótimo (§5.2).
    Se o tempo ou o número de relaxações acabar antes, o algoritmo devolve a melhor solução e o menor limite inferior em aberto,
    portanto uma garantia de quão longe do ótimo ela pode estar.
    """)
    return


@app.cell(hide_code=True)
def _(C, codigo, mo):
    _texto = mo.md(r"""
    ### 3.2 Código

    Primeiro, a heurística que melhora um ponto inteiro mexendo numa coordenada de cada vez, a análise das variáveis livres
    e a regra de ramificação:
    """)
    mo.vstack([_texto, codigo(C.melhoria_local, C._analise_livres, C._escolher_variavel)])
    return


@app.cell(hide_code=True)
def _(C, codigo, mo):
    _texto = mo.md(r"""
    O ciclo principal:
    """)
    mo.vstack([_texto, codigo(C.branch_and_bound)])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 3.3 A poda barata
    Antes de chamar o solver para um filho $z_i=a$, calcula-se um limite inferior à custa de álgebra linear. A relaxação com
    os limites $0\le z\le\ell$ é pelo menos tão grande como a relaxação sem eles, isto é, o problema de mínimos quadrados nas
    variáveis livres. Se $z^{*}$ é o ótimo desse problema e $r^{*}$ o seu resíduo, fixar $z_i=a$ dá exatamente
    $$\text{dist}^2 \;=\; r^{*2}+\big((a-z_i^{*})\,d_i\big)^2 ,$$
    e este valor é um limite inferior válido para o filho. Se já for $\ge U$, o filho nem chega a ser resolvido. É uma
    otimização que não altera o resultado (a §5.2 mostra o ótimo igual com e sem ela e quantas relaxações poupa).

    ### 3.4 Nota sobre a exatidão
    * Os solvers cónicos são numéricos, por isso compara-se com uma tolerância (`TOL_PODA`, $10^{-6}$): declara-se ótimo quando
      nenhum nó aberto pode melhorar a melhor distância em mais do que isso.
    * A solução devolvida é sempre inteira e admissível; só o limite inferior depende da precisão do solver.
    """)
    return


@app.cell(hide_code=True)
def _(C, SOLVER, mo, tabela):
    _linhas = []
    for _k, _l in [(6, 1), (10, 1), (6, 5), (8, 2)]:
        _inst = C.gerar_instancia(_k, 2 * _k, _l, semente=3)
        _r = C.branch_and_bound(_inst, SOLVER)
        _zfb, _dfb = C.forca_bruta(_inst)
        _zes, _des = C.esfera_exata(_inst)
        _ok = abs(_r.dist - _dfb) < 1e-6 and abs(_des - _dfb) < 1e-6
        _linhas.append([_k, _l, f"{_r.dist:.6f}", f"{_dfb:.6f}", f"{_des:.6f}", "sim" if _ok else "NÃO",
                        _r.nos, f"{_r.segundos:.2f}"])
    _inst = C.gerar_instancia(8, 16, 2, semente=3)
    _r = C.branch_and_bound(_inst, SOLVER)
    mo.md(
        "## 4. Resultados\n\n### 4.1 Instâncias pequenas, contra métodos exatos\n\n"
        "Nas instâncias pequenas pode-se testar todos os $(\\ell+1)^k$ pontos (força bruta). Compara-se o branch-and-bound com a "
        "força bruta e com uma enumeração exata por esfera (Schnorr-Euchner sobre a decomposição QR de $A$), que não usa relaxações:\n\n"
        + tabela(["k", "ℓ", "branch-and-bound", "força bruta", "esfera", "coincidem", "relaxações", "tempo (s)"], _linhas)
        + f"\n\nPara $k=8$, $\\ell=2$ a solução encontrada é $z={[int(v) for v in _r.z]}$, com distância ${_r.dist:.4f}$ ao alvo."
    )
    return


@app.cell(hide_code=True)
def _(mo):
    executar = mo.ui.switch(value=False, label="Correr as instâncias do enunciado (k=30, 40, 50) e a tabela de escala; demora vários minutos")
    mo.vstack([
        mo.md(r"""
        ### 4.2 As instâncias do enunciado e a escala

        Para $k=30,40,50$, $m=2k$ e $\ell\in\{1,5\}$ (e, para ver o crescimento, também $k=10,20$) corre-se o branch-and-bound com um limite
        de tempo por instância (`LIMITE_S`, no código da célula seguinte). Quando o limite acaba antes da prova, a tabela mostra a melhor
        solução, o limite inferior e a folga. Como referência do valor ótimo usa-se a enumeração por esfera (que não usa o solver cónico).

        Para repetir os cálculos, ative o interruptor. Para exportar o PDF com os resultados, deixe-o ativo.
        """),
        executar,
    ])
    return (executar,)


@app.cell(hide_code=True)
def _(C, SOLVER, executar, mo, tabela):
    LIMITE_S = 120          # segundos por instância
    if not executar.value:
        _saida = mo.callout(mo.md("Interruptor desligado: as instâncias do enunciado ainda não foram corridas."), kind="neutral")
    else:
        _linhas = []
        for _k in (10, 20, 30, 40, 50):
            for _l in (1, 5):
                _inst = C.gerar_instancia(_k, 2 * _k, _l, semente=1)
                _r = C.branch_and_bound(_inst, SOLVER, limite_s=LIMITE_S)
                _zex, _dex = C.esfera_exata(_inst, max_nos=3_000_000)
                _estado = "ótimo provado" if _r.otimo else f"parou ({LIMITE_S} s)"
                _ref = "n/d" if _dex is None else f"{_dex:.4f}"
                _ok = "n/d" if _dex is None else ("sim" if abs(_r.dist - _dex) < 1e-5 else f"não (+{_r.dist - _dex:.4f})")
                _linhas.append([_k, 2 * _k, _l, _estado, f"{_r.dist:.4f}", f"{_r.limite_inf:.4f}", f"{_r.folga:.4f}",
                                _ref, _ok, _r.nos, _r.podados, f"{_r.segundos:.1f}"])
        _saida = mo.md(
            tabela(["k", "m", "ℓ", "estado", "distância", "limite inferior", "folga", "ótimo exato", "coincide",
                    "relaxações", "podados", "tempo (s)"], _linhas)
            + "\n\n«Relaxações» conta os problemas cónicos resolvidos e «podados» os filhos eliminados pela poda barata sem resolver nada."
        )
    _saida
    return


@app.cell(hide_code=True)
def _(T, codigo, mo):
    _texto = mo.md(r"""
    ---
    ## 5. Validação: correção, eficiência e escala

    ### 5.1 Correção: testes com `pytest`

    | Grupo | O que garante |
    |:--|:--|
    | Instâncias | $G$ com entradas em $[0,1]$, característica $k$, $t=G^\top u$ com componentes positivas; a verificação da base deteta vetores dependentes; parâmetros inválidos são recusados |
    | Relaxação | o Clarabel dá a mesma distância que o resolvedor de apoio, respeita as variáveis fixas, e a relaxação é limite inferior do ótimo inteiro |
    | Branch-and-bound | coincide com a força bruta em dezenas de instâncias pequenas, com a esfera exata em instâncias médias, e com todas as regras de ramificação |
    | Limites | com limite de tempo ou de relaxações devolve limite inferior $\le$ ótimo $\le$ distância encontrada; a melhor solução só desce |
    | Casos extremos | $k=m$; alvo dentro do reticulado (distância 0) |

    Dois exemplos:
    """)
    mo.vstack([_texto, codigo(T.test_bb_coincide_com_a_forca_bruta, T.test_bb_com_limite_de_nos_devolve_limites_coerentes)])
    return


@app.cell(hide_code=True)
def _(Path, mo, subprocess, sys):
    _pasta = Path(__file__).resolve().parent
    _p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                        cwd=_pasta, capture_output=True, text=True, timeout=1800)
    _ok = _p.returncode == 0
    mo.vstack([
        mo.md("Resultado de executar `pytest` neste momento:\n\n```text\n" + (_p.stdout + _p.stderr).strip() + "\n```"),
        mo.callout(mo.md("Todos os testes passam." if _ok else "Há testes a falhar (ver acima)."),
                   kind="success" if _ok else "danger"),
    ])
    return


@app.cell(hide_code=True)
def _(C, SOLVER, mo, tabela):
    _inst = C.gerar_instancia(12, 24, 5, semente=1)
    _variantes = [
        ("regra «perp» com poda barata (a usada)", dict(regra="perp", poda_barata=True)),
        ("regra «perp» sem poda barata", dict(regra="perp", poda_barata=False)),
        ("variável mais fracionária, com poda barata", dict(regra="fracionaria", poda_barata=True)),
        ("primeira variável livre, com poda barata", dict(regra="indice", poda_barata=True)),
    ]
    _linhas = []
    for _nome, _kw in _variantes:
        _r = C.branch_and_bound(_inst, SOLVER, **_kw)
        _linhas.append([_nome, f"{_r.dist:.6f}", "sim" if _r.otimo else "não", _r.nos, _r.podados, f"{_r.segundos:.2f}"])
    mo.md(
        "### 5.2 Eficiência: o que poupa cada decisão\n\n"
        "Mesma instância ($k=12$, $m=24$, $\\ell=5$) com variantes do algoritmo. O ótimo tem de ser igual em todas; "
        "o que muda é o número de problemas cónicos resolvidos.\n\n"
        + tabela(["variante", "distância", "ótimo provado", "relaxações", "podados", "tempo (s)"], _linhas)
        + "\n\nA poda barata evita muitas chamadas ao solver sem mudar o resultado. Nesta instância a escolha da regra de ramificação pesa bem menos."
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 5.3 Escala
    A tabela da §4.2 mostra como o número de relaxações e o tempo crescem com $k$ e $\ell$. A razão é que o número de nós da árvore
    cresce depressa com a dimensão: a relaxação na raiz dá limite inferior 0 (§2.2), e só quando se fixam muitas variáveis é que o
    limite se aproxima da distância ótima. Isso é uma propriedade do CVP, que é um problema difícil, e não de uma implementação concreta.
    A enumeração por esfera usa o mesmo tipo de pesquisa, mas cada nó custa muito menos que um problema cónico, e por isso serve de referência.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ## 6. Conclusões

    * O CVP com coeficientes limitados escreve-se como um problema cónico de segunda ordem quando se relaxa a integralidade. Com `cvxpy` isto
      resume-se a minimizar `cp.norm(A @ z - t, 2)` com $0\le z\le\ell$, e o Clarabel resolve-o.
    * Os inteiros são tratados por um branch-and-bound, com relaxação cónica em cada nó, ramificação em todos os valores de uma variável,
      escolha de nó *best-first*, uma heurística de arredondamento e melhoria local e uma poda barata que não altera o resultado.
    * Os resultados do branch-and-bound coincidem com os de dois métodos exatos independentes (força bruta e enumeração por esfera) em todas as
      instâncias testadas.
    * Se o tempo acaba antes da prova, o algoritmo devolve uma solução admissível com o limite inferior, isto é, quão longe do ótimo pode estar.

    Limitações:

    * O custo cresce depressa com $k$ e $\ell$ (§5.3). Para as instâncias maiores o branch-and-bound pode não chegar a provar a otimalidade no tempo dado.
    * Cada nó resolve uma relaxação construída de raiz com `cvxpy`; a compilação do modelo pesa no tempo total.
    * O `Mosek`, que tem tratamento de inteiros, não foi usado por exigir licença.
    * Os tempos dependem da máquina e da versão do `cvxpy` e do Clarabel.


    ## 7. Diálogo com ferramentas LLM

    Foi usado o Claude (Anthropic) como apoio: para perceber a formulação cónica do CVP, discutir
    o desenho do branch-and-bound e do plano de testes, e rever o código. Os testes e os resultados foram executados
    e verificados por nós.
     Conversa: [https://claude.ai/share/0151a521-440e-4f75-81bf-25279af6f122]


    ---
    ## Apêndice: como executar

    ```bash
    cd TP2
    python3 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cd ex2
    pytest                                               # testes rápidos
    pytest -m slow                                       # instâncias maiores
    marimo edit ex2_cvp.py --no-sandbox                  # abrir o notebook
    marimo run  ex2_cvp.py --no-sandbox                  # só leitura
    marimo export html ex2_cvp.py -o ex2.html            # exportar (depois imprimir para PDF)
    ```
    """)
    return


if __name__ == "__main__":
    app.run()
