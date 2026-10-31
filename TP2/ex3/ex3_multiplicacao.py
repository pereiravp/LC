import marimo

__generated_with = "0.20.0"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import inspect
    import subprocess
    import sys
    import textwrap
    import time
    from pathlib import Path

    import marimo as mo
    from z3 import Not

    import sfots_mult as M
    import test_sfots_mult as T

    def codigo(*objetos):
        """Mostra o código-fonte de funções e classes como bloco de código."""
        fonte = "\n\n".join(textwrap.dedent(inspect.getsource(o)).rstrip() for o in objetos)
        return mo.md("```python\n" + fonte + "\n```")

    def tabela(cabecalho, linhas):
        """Tabela em Markdown a partir de uma lista de linhas."""
        cab = "| " + " | ".join(cabecalho) + " |"
        sep = "|" + "|".join("---" for _ in cabecalho) + "|"
        corpo = ["| " + " | ".join(str(c) for c in linha) + " |" for linha in linhas]
        return "\n".join([cab, sep] + corpo)

    return M, Not, Path, T, codigo, mo, subprocess, sys, tabela, time


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # TP2 · Exercício 3: verificação formal da multiplicação de inteiros

    SFOTS em Z3 com `BitVec`, $k$-indução e propriedade de animação

    Lógica Computacional 2026/27 · Licenciatura em Ciências da Computação · Universidade do Minho

    Grupo 21: Gonçalo Pereira (111783) e David Mimoso (111115)

    ---

    ## Resumo

    O programa estudado multiplica dois inteiros sem sinal, representados com $n$ bits, usando apenas somas,
    duplicações e metades. Em vez de o testar com alguns valores, modelamo-lo como um sistema de transições
    (SFOTS) em Z3 e provamos quatro coisas para todos os valores possíveis: a descrição do modelo, um invariante
    ($x\cdot y+z=a\cdot b$), a ausência de overflow quando $a,b<2^{n/2}$ e a terminação do programa.

    ## Correspondência com o enunciado
    """)
    return


@app.cell(hide_code=True)
def _(mo, tabela):
    mo.md(tabela(
        ["Enunciado", "O que se pede", "Onde está"],
        [
            ["3.1", "SFOTS com `BitVec` de tamanho $n$: variáveis, estado inicial, relação de transição e estado de erro", "§2 (2.1 a 2.4)"],
            ["3.2", "Verificar por $k$-indução que $x\\cdot y+z=a\\cdot b$ é invariante", "§3"],
            ["3.3", "Com $(a<2^{n/2})\\wedge(b<2^{n/2})$ no estado inicial, provar por $k$-indução que o erro nunca é acessível", "§4"],
            ["3.4", "Codificar e provar a propriedade de animação: o programa termina, quaisquer que sejam $a$ e $b$", "§5"],
            ["Regras gerais", "Descrição do problema e da abordagem; código; testes de correção, eficiência e escala", "§1 a §5 e §6"],
            ["Regras gerais", "Diálogo com ferramentas LLM", "§8"],
            ["Extras", "O enunciado não tem secção de extras. Incluem-se a otimização e o estudo de escala (§6.2, §6.3) e a verificação da segurança com PDR (§4.6)", "§4.6, §6"],
        ],
    ))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.callout(mo.md(r"""
    O código do modelo e dos verificadores está em `sfots_mult.py`, e os testes em `test_sfots_mult.py`; o notebook mostra
    os excertos relevantes junto da explicação. Os resultados das tabelas são calculados pelo Z3 quando o notebook corre.
    A única exceção é a tabela de tempos de referência da §6.3, que está assinalada.
    """), kind="info")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ## 1. O problema

    ### 1.1 O programa
    É o modelo CFA do Capítulo 4 (2.ª parte), «Multiplicação de inteiros com erros». As variáveis são vetores de
    $n$ bits sem sinal e $a$, $b$ são os valores iniciais:

    ```python
    x, y, z = a, b, 0
    while y != 0:
        if y é par:   x, y = 2*x, y // 2       # dobra x e divide y por 2   (local even)
        else:         z, y = z + x, y - 1      # soma x a z e torna y par   (local odd)
        # se 2*x ou z+x não couber em n bits há overflow e o programa vai para error
    # aqui y == 0 (local stop) e z deve valer a*b
    ```

    ### 1.2 Porque é que dá o produto
    Em todos os passos $x\cdot y+z$ é igual a $a\cdot b$. Dobrar $x$ e dividir $y$ por 2 não altera $x\cdot y$;
    somar $x$ a $z$ e tirar 1 a $y$ passa de $x\cdot y$ para $z$ exatamente o que se perde em $x\cdot y$.
    Quando $y=0$ sobra $z=a\cdot b$. Execução com $a=3$ e $b=5$ (a última coluna é constante):
    """)
    return


@app.cell(hide_code=True)
def _(M, mo, tabela):
    _n, _a, _b = 8, 3, 5
    _linhas = [[i, pc, x, y, z, x * y + z] for i, (pc, x, y, z) in enumerate(M.traco_ref(_a, _b, _n))]
    mo.md(f"Execução com $a={_a}$, $b={_b}$ e $n={_n}$ bits:\n\n" + tabela(["passo", "pc", "x", "y", "z", "x·y + z"], _linhas))
    return


@app.cell(hide_code=True)
def _(M, mo, tabela):
    _n, _a, _b = 8, 16, 16
    _linhas = [[i, pc, x, y, z] for i, (pc, x, y, z) in enumerate(M.traco_ref(_a, _b, _n))]
    mo.md(
        f"### 1.3 Overflow\n\n"
        f"Com $n={_n}$ bits só cabem valores até $2^{{{_n}}}-1=255$. Para $a={_a}$ e $b={_b}$ o produto é "
        f"${_a*_b}$ e não cabe, pelo que o programa termina em `ERROR`:\n\n"
        + tabela(["passo", "pc", "x", "y", "z"], _linhas)
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 1.4 O que vamos provar

    | # | Pergunta | Formulação |
    |:-:|:--|:--|
    | 1 | Como descrever o programa para que um solver o analise? | SFOTS $\langle X,I,T,E\rangle$ |
    | 2 | A relação $x\cdot y+z=a\cdot b$ vale em todos os passos? | invariante, $G\,P$ |
    | 3 | Se $a$ e $b$ forem pequenos, nunca há overflow? | segurança, $G\,\neg E$ |
    | 4 | O programa termina sempre, para quaisquer $a$ e $b$? | animação, $F\,\text{parado}$ |

    Termos usados:

    * **SFOTS** (*safe first-order transition system*): estados dados por valores de variáveis numa teoria (aqui, vetores de bits),
      com um predicado de estados iniciais $I$, uma relação de transição $T(s,s')$ e um predicado de erro $E$.
    * **Invariante**: afirmação verdadeira no estado inicial e preservada por cada transição.
    * **$k$-indução**: prova de um invariante olhando para janelas de $k$ estados consecutivos (com $k=1$ é a indução simples).
    * **BMC** (*bounded model checking*): procura de um traço de comprimento limitado; é o que usamos para obter contra-exemplos.
    * **Propriedade de animação**: algo que tem de acontecer ($F\,P$, «eventualmente $P$»), por oposição às de segurança, que dizem que algo nunca acontece.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ## 2. Ponto 3.1: construir o SFOTS em Z3

    Um SFOTS tem quatro componentes, que identificamos e codificamos uma a uma:
    (2.1) variáveis $X$, (2.2) estado inicial $I$, (2.3) relação de transição $T$ e (2.4) estado de erro $E$.

    Duas decisões de modelação:

    1. Locais. Os locais `even` e `odd` apenas atribuem e testam o overflow, por isso são fundidos na transição que parte de `do`:
       um passo do SFOTS escolhe o ramo pela paridade de $y$, faz a atribuição e testa o overflow. O *program counter* é um tipo
       enumerado com três valores, `DO`, `STOP` e `ERROR`. O capítulo observa que `error` não corresponde a uma posição do contador
       de um programa imperativo e que inventar números fictícios para o `pc` é fonte de erros; o tipo enumerado evita isso, e o erro
       fica como o predicado $E\equiv(pc=\text{ERROR})$.
    2. Totalidade. `STOP` e `ERROR` repetem o estado (são *sinks*), de modo que todo o estado tem sucessor e os traços são infinitos.
    """)
    return


@app.cell(hide_code=True)
def _(M, codigo, mo):
    _texto = mo.md(r"""
    ### 2.1 Variáveis do modelo, $X=(pc,\,a,\,b,\,x,\,y,\,z)$

    | Variável | Tipo Z3 | Papel |
    |:--|:--|:--|
    | `pc` | enumerado `{DO, STOP, ERROR}` | posição do controlo |
    | `a`, `b` | `BitVec(n)` | valores iniciais; não mudam ($a'=a$, $b'=b$). Fazem parte do estado para que $x\,y+z=a\,b$ seja um predicado do estado |
    | `x`, `y`, `z` | `BitVec(n)` | variáveis do programa |

    O operador `next` do SFOTS, que cria os «clones» $X'$, $X_0$, $X_1$, …, é a função `novo_estado(n, etiqueta)`,
    que devolve variáveis frescas com a etiqueta indicada:
    """)
    mo.vstack([_texto, codigo(M.Estado, M.novo_estado)])
    return


@app.cell(hide_code=True)
def _(M, codigo, mo):
    _texto = mo.md(r"""
    ### 2.2 Estado inicial $I$

    O CFA começa com `havoc(a,b)` (valores arbitrários) seguido da guarda $(x=a)\wedge(y=b)\wedge(z=0)$. Logo
    $$I\;\equiv\;(pc=\text{DO})\wedge(x=a)\wedge(y=b)\wedge(z=0),\qquad a,b\ \text{livres}.$$
    Com `restringir_entradas=True` junta-se a condição do ponto 3.3, $(a<2^{n/2})\wedge(b<2^{n/2})$.
    """)
    mo.vstack([_texto, codigo(M.MultiplicacaoSFOTS.__init__, M.MultiplicacaoSFOTS.init)])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 2.3 Relação de transição $T$

    $T$ é a disjunção de cinco ramos, que não se sobrepõem e cobrem todos os estados, juntamente com a condição $a'=a\wedge b'=b$:

    | Ramo | Guarda | Efeito | Novo `pc` |
    |:--|:--|:--|:--|
    | `stop` | $pc=\text{DO}\wedge y=0$ | nada muda | `STOP` |
    | `even` | $pc=\text{DO}\wedge y\neq0\wedge y\ \text{par}$ | $x'=2x,\ y'=y/2,\ z'=z$ | `ERROR` se há overflow, senão `DO` |
    | `odd` | $pc=\text{DO}\wedge y\ \text{ímpar}$ | $z'=z+x,\ y'=y-1,\ x'=x$ | `ERROR` se há overflow, senão `DO` |
    | `sink_s` | $pc=\text{STOP}$ | repete o estado | `STOP` |
    | `sink_e` | $pc=\text{ERROR}$ | repete o estado | `ERROR` |

    Overflow, em aritmética sem sinal de $n$ bits: dobrar $x$ perde o bit mais significativo quando `Extract(n-1, n-1, x) = 1`;
    somar $z+x$ ultrapassa $2^n-1$ quando `¬BVAddNoOverflow(z, x, False)`. A paridade de $y$ é o bit menos significativo,
    `Extract(0, 0, y)`, e dividir por 2 é o deslocamento `LShR(y, 1)`.
    """)
    return


@app.cell(hide_code=True)
def _(M, codigo):
    codigo(M.MultiplicacaoSFOTS.guardas, M.MultiplicacaoSFOTS.ramos, M.MultiplicacaoSFOTS.trans)
    return


@app.cell(hide_code=True)
def _(M, codigo, mo):
    _texto = mo.md(r"""
    ### 2.4 Estado de erro $E$ e estados de paragem

    O erro é $E\equiv(pc=\text{ERROR})$. Para a propriedade de animação (§5) usa-se ainda o predicado
    $\text{parado}\equiv pc\in\{\text{STOP},\text{ERROR}\}$.
    """)
    mo.vstack([_texto, codigo(M.MultiplicacaoSFOTS.erro, M.MultiplicacaoSFOTS.parado)])
    return


@app.cell(hide_code=True)
def _(M, codigo, mo, tabela):
    _linhas = []
    for _a, _b in [(3, 5), (15, 15), (0, 7), (7, 0), (16, 16), (255, 255)]:
        _pc, _x, _y, _z, _p = M.referencia(_a, _b, 8)
        _linhas.append([_a, _b, _pc, _z if _pc == "STOP" else "-", _a * _b, _p])
    _texto = mo.md(
        "### 2.5 O modelo descreve o programa?\n\n"
        "Antes de provar propriedades, convém garantir que o SFOTS descreve o programa. Para isso escrevemos um simulador "
        "em Python puro, sem Z3 (`passo_ref` e `referencia`), e os testes (§6.1) verificam que, para estados arbitrários, "
        "a transição Z3 tem exatamente um sucessor e que este coincide com o do simulador. "
        "Exemplos com $n=8$ (`-` indica que o programa terminou em `ERROR`):\n\n"
        + tabela(["a", "b", "estado final", "z", "a·b", "nº de passos"], _linhas)
    )
    mo.vstack([_texto, codigo(M.passo_ref, M.referencia)])
    return


@app.cell(hide_code=True)
def _(M, codigo, mo):
    _texto = mo.md(r"""
    ---
    ## 3. Ponto 3.2: $x\cdot y+z=a\cdot b$ é invariante?

    Prova-se $G\,P$ por $k$-indução (Cap. 3) mostrando que são impossíveis (`unsat`) as duas condições:

    * (a) base, para $j=0,\dots,k-1$: $\;I(X_0)\wedge\bigwedge_{i<j}T(X_i,X_{i+1})\wedge\neg P(X_j)$
    * (b) passo: $\;\bigwedge_{i<k}\big(P(X_i)\wedge T(X_i,X_{i+1})\big)\wedge\neg P(X_k)$

    Ou seja, $P$ vale nos primeiros $k$ estados a partir do início e, se vale em $k$ estados seguidos, vale também no seguinte.
    Aqui basta $k=1$, e a aritmética é a de $n$ bits (módulo $2^n$). Código:
    """)
    mo.vstack([_texto, codigo(M.invariante_produto, M.k_inducao)])
    return


@app.cell(hide_code=True)
def _(M, mo, tabela):
    _linhas = []
    for _n in (4, 6, 8, 10):
        _sf = M.MultiplicacaoSFOTS(_n)
        _r = M.k_inducao(_sf, M.invariante_produto(_sf), k=1, timeout_ms=120_000, dividir_ramos=True)
        _linhas.append([_n, 1, _r.base_ok, _r.passo_ok, f"{_r.segundos:.2f}", f"{_r.veredicto}"])
    _errado = lambda s: s.x * s.y + s.z == s.a * s.b + 1
    _neg = M.k_inducao(M.MultiplicacaoSFOTS(6), _errado, k=1)
    mo.vstack([
        mo.md("Resultado (a opção `dividir_ramos` é uma otimização de velocidade, descrita na §6.2, que não altera nenhum veredicto):\n\n"
              + tabela(["n", "k", "(a) base", "(b) passo", "tempo (s)", "veredicto"], _linhas)),
        mo.callout(mo.md(
            "Conclusão: o invariante é $1$-indutivo. Vale no estado inicial e cada ramo o preserva (par, ímpar e paragem). "
            "Como a aritmética é módulo $2^n$, vale também quando há overflow."), kind="success"),
        mo.md(f"Como controlo, um invariante falso, $x\\,y+z=a\\,b+1$, tem de ser recusado: o veredicto foi "
              f"{_neg.veredicto}, com o estado inicial `{_neg.contra_exemplo[0]}` como contra-exemplo."),
    ])
    return


@app.cell(hide_code=True)
def _(M, codigo, mo):
    _texto = mo.md(r"""
    ---
    ## 4. Ponto 3.3: com $a,b<2^{n/2}$ o erro nunca é acessível

    O estado inicial passa a $I'\equiv I\wedge(a<2^{n/2})\wedge(b<2^{n/2})$, o que garante $a\cdot b<2^{n/2}\cdot2^{n/2}=2^n$:
    o produto final cabe em $n$ bits. Falta ver que nenhum passo intermédio provoca overflow. A propriedade é
    $P\equiv\neg E=(pc\neq\text{ERROR})$.

    ### 4.1 Primeira tentativa: $k$-indução de $P$ sozinha
    """)
    mo.vstack([_texto, codigo(M.seguranca_simples)])
    return


@app.cell(hide_code=True)
def _(M, mo, tabela):
    _n = 8
    _sf = M.MultiplicacaoSFOTS(_n, restringir_entradas=True)
    _linhas, _cex = [], None
    for _k in range(1, 7):
        _r = M.k_inducao(_sf, M.seguranca_simples(_sf), k=_k)
        _linhas.append([_k, _r.base_ok, _r.passo_ok, f"{_r.veredicto}"])
        if _k == 1:
            _cex = _r.contra_exemplo
    mo.md(
        f"Com $n={_n}$:\n\n" + tabela(["k", "(a) base", "(b) passo", "veredicto"], _linhas)
        + "\n\nA base vale, mas o passo falha para estes $k$ (todos abaixo de $2n$; ver §4.4). O passo (b) considera todos os estados que cumprem "
          "$P$, não apenas os alcançáveis. O contra-exemplo seguinte é um estado arbitrário (não alcançável) com $pc\\neq$ ERROR "
          "que salta para ERROR num passo, porque dobrar $x$ ou somar $z+x$ já não cabe em $n$ bits:\n\n"
          f"```text\n{_cex[0]}\n  --T-->  {_cex[1]}\n```\n\n"
          "Com $k$ pequeno a indução não vê porque é que o overflow não acontece. Há dois caminhos: reforçar a propriedade (§4.2 e §4.3) ou subir $k$ até $2n$ (§4.4)."
    )
    return


@app.cell(hide_code=True)
def _(M, codigo, mo):
    _texto = mo.md(r"""
    ### 4.2 Reforço da propriedade

    O que evita o overflow é o invariante do ponto 3.2 lido sem módulo, isto é, calculado em $2n$ bits (onde nada transborda):
    $$x\,y+z=a\,b\ \ (\text{em }\mathbb{N}),\qquad a\,b<2^{n}.$$

    * Ramo par: como $y\ge2$, tem-se $x\le x\,y/2\le a\,b/2<2^{n-1}$, o bit mais significativo de $x$ é 0 e $2x$ cabe.
    * Ramo ímpar: como $y\ge1$, tem-se $z+x\le z+x\,y=a\,b<2^{n}$ e a soma cabe.

    A propriedade reforçada é
    $$Q\;\equiv\;\neg E\ \wedge\ \big(x\,y+z=a\,b\ \text{ em }2n\text{ bits}\big)\ \wedge\ a<2^{n/2}\ \wedge\ b<2^{n/2},$$
    que implica $P$. Se $Q$ for $k$-indutiva fica provado $G\,Q$ e, portanto, $G\,\neg E$. Note-se que $Q\Rightarrow\neg E$ é imediato (está dentro de $Q$): o trabalho está no passo de indução, onde a identidade larga e os limites de $a$ e $b$ mostram que o próximo estado também não é de erro.
    """)
    mo.vstack([_texto, codigo(M.MultiplicacaoSFOTS.produto_largo, M.MultiplicacaoSFOTS.ab_largo, M.seguranca_reforcada)])
    return


@app.cell(hide_code=True)
def _(M, mo, tabela):
    _linhas = []
    for _n in (4, 6, 8, 10):
        _sf = M.MultiplicacaoSFOTS(_n, restringir_entradas=True)
        _r = M.k_inducao(_sf, M.seguranca_reforcada(_sf), k=1, timeout_ms=300_000, dividir_ramos=True)
        _linhas.append([_n, 1, _r.base_ok, _r.passo_ok, f"{_r.segundos:.2f}", f"{_r.veredicto}"])
    mo.vstack([
        mo.md("### 4.3 Prova\n\n" + tabela(["n", "k", "(a) base", "(b) passo", "tempo (s)", "veredicto"], _linhas)),
        mo.callout(mo.md(
            "Conclusão: $Q$ é $1$-indutiva e $Q\\Rightarrow\\neg E$. Logo, com $a,b<2^{n/2}$ no estado inicial, o estado de erro "
            "nunca é acessível. (Confirmado também por BMC e por força bruta, §6.1.)"), kind="success"),
    ])
    return


@app.cell(hide_code=True)
def _(M, mo, tabela):
    _linhas = []
    for _n in (4, 6, 8, 10):
        _sf = M.MultiplicacaoSFOTS(_n, restringir_entradas=True)
        _res = {}
        for _k in (2 * _n - 1, 2 * _n):
            _res[_k] = M.k_inducao(_sf, M.seguranca_simples(_sf), k=_k, timeout_ms=120_000)
        _p, _q = _res[2 * _n - 1], _res[2 * _n]
        _linhas.append([_n, 2 * _n - 1, _p.veredicto, 2 * _n, _q.veredicto, f"{_q.segundos:.2f}"])
    mo.vstack([
        mo.md(
            "### 4.4 Segunda via: $\\neg E$ é $k$-indutivo para $k\\ge2n$\n\n"
            "Há uma prova sem reforço, só com $k$ grande. Uma janela de $k$ estados sem erro seguida de um erro tem de ser "
            "toda de estados `DO` (`STOP` e `ERROR` são sinks). Mas o programa não dá mais de $2n-1$ passos `DO` seguidos, "
            "porque $y$ chega a 0 (§5.5). Com $k\\ge2n$ não há janela deste tipo, e a restrição $a,b<2^{n/2}$ só é usada na base, "
            "onde garante que o erro não é alcançável em $k-1$ passos.\n\n"
            + tabela(["n", "k = 2n−1", "veredicto", "k = 2n", "veredicto", "tempo (s)"], _linhas)
        ),
        mo.callout(mo.md(
            "Conclusão: $\\neg E$ sozinho passa a ser $k$-indutivo exatamente a partir de $k=2n$, o mesmo limite da terminação. "
            "Temos assim duas provas independentes do ponto 3.3: o reforço $Q$ com $k=1$ e $\\neg E$ com $k=2n$."), kind="success"),
    ])
    return


@app.cell(hide_code=True)
def _(M, codigo, mo, tabela):
    _n = 8
    _sf = M.MultiplicacaoSFOTS(_n)
    _veredicto, _traco = M.bmc_alcanca(_sf, _sf.erro, K=2 * _n)
    _a, _b = _traco[0]["a"], _traco[0]["b"]
    _linhas = [[i, e["pc"], e["x"], e["y"], e["z"]] for i, e in enumerate(_traco) if i == 0 or _traco[i - 1]["pc"] == "DO"]
    _texto = mo.md(
        "### 4.5 Sem a restrição o erro é acessível\n\n"
        f"Retirando $a,b<2^{{n/2}}$, o BMC (traços até $2n={2*_n}$ passos, com $n={_n}$) responde {_veredicto} e dá "
        f"um contra-exemplo: $a={_a}$, $b={_b}$, com $a\\cdot b={_a*_b}\\ge2^{{{_n}}}$. O simulador confirma: "
        f"`{M.referencia(_a, _b, _n)[0]}`. A restrição do enunciado é, portanto, necessária.\n\n"
        + tabela(["passo", "pc", "x", "y", "z"], _linhas)
        + "\n\nCódigo do BMC:"
    )
    mo.vstack([_texto, codigo(M.bmc_alcanca)])
    return


@app.cell(hide_code=True)
def _(M, codigo, mo, tabela, time):
    _linhas = []
    for _n in (4, 6, 8):
        _t = []
        for _restr in (True, False):
            _t0 = time.perf_counter()
            _r = M.pdr_isolado(_n, _restr, timeout_s=120)
            _t.append(f"{_r} ({time.perf_counter() - _t0:.1f} s)")
        _linhas.append([_n] + _t)
    _texto = mo.md(r"""
    ### 4.6 Extra: segurança com PDR

    A $k$-indução precisou de um reforço escolhido à mão ($Q$). O algoritmo PDR (*property directed reachability*, Cap. 4), que no Z3
    é o motor Spacer, procura sozinho um invariante indutivo. O sistema escreve-se como cláusulas de Horn sobre um predicado
    $\text{Inv}$ (os estados acessíveis):
    $I\to\text{Inv}$, $\ \text{Inv}\wedge T\to\text{Inv}'$ e $\ \text{Inv}\wedge E\to\bot$.
    A resposta `unsat` significa que o PDR encontrou um invariante que exclui o erro, e `sat` que o erro é acessível.
    """)
    mo.vstack([
        _texto,
        codigo(M.pdr_erro_acessivel, M.pdr_isolado),
        mo.md(tabela(["n", "com a,b < 2^(n/2)", "com a,b quaisquer"], _linhas)
              + "\n\nO PDR chega à mesma conclusão que a $k$-indução reforçada (com restrição o erro é inacessível; sem ela é acessível) "
                "sem que se lhe dê o reforço. O custo cresce com $n$: com $n=10$ demorou cerca de 30 s e com "
                "$n=12$ excedeu os 120 s (medições feitas antes, nesta máquina)."),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ## 5. Ponto 3.4: o programa termina sempre

    ### 5.1 Significado de «termina»
    O programa pára de duas maneiras: em `STOP` (terminou normalmente) ou em `ERROR` (overflow). Para $a,b$ quaisquer,
    como pede o enunciado, a propriedade é
    $$F\ \text{parado},\qquad \text{parado}\equiv pc\in\{\text{STOP},\text{ERROR}\}.$$
    Com $a,b<2^{n/2}$ o §4 exclui `ERROR`, e o programa pára sempre em `STOP` (§5.6).

    ### 5.2 Porque não basta a $k$-indução
    A $k$-indução prova propriedades de segurança, $G\,P$. A terminação é uma propriedade de animação, $F\,P$. O capítulo 3
    («*Look aheads*») resolve-a com um predicado auxiliar $P^*$ que olha para a frente e converte $F$ em $G$.

    ### 5.3 Ideia
    Em cada volta do ciclo $y$ diminui. Como $y$ é um número natural, não pode diminuir indefinidamente. Para tratar também a passagem
    de `DO` para o ramo seguinte usa-se a medida
    $$R(s)=2\,y+[pc=\text{DO}]\qquad(\text{em }n{+}1\text{ bits, sem overflow}).$$
    O predicado binário, que compara o estado com o seguinte, é
    $$P^*(s,s')\;\equiv\;\big(\neg\text{parado}(s)\to R(s')<R(s)\big)\ \wedge\ \big(\text{parado}(s)\to s'=s\big).$$
    Se $G\,P^*$ vale, $R$ desce estritamente enquanto o programa não pára e, como em $\mathbb N$ não há descidas infinitas,
    o programa pára: $G\,P^*\Rightarrow F\,\text{parado}$. A prova de $G\,P^*$ é por indução, com quatro condições (3 clones $X,Y,Z$):

    1. `parado` é indutivo: $\text{parado}(X)\wedge T(X,Y)\wedge\neg\text{parado}(Y)$ é `unsat`;
    2. $T$ é total: todo o estado tem sucessor;
    3. $P^*$ é indutivo: $P^*(X,Y)\wedge T(X,Y)\wedge T(Y,Z)\wedge\neg P^*(Y,Z)$ é `unsat`;
    4. $P^*$ vale no início: $I(X)\wedge T(X,Y)\wedge\neg P^*(X,Y)$ é `unsat`.
    """)
    return


@app.cell(hide_code=True)
def _(M, codigo, mo):
    mo.vstack([mo.md("### 5.4 Código e resultado"), codigo(M.MultiplicacaoSFOTS.medida, M.p_estrela, M.animacao)])
    return


@app.cell(hide_code=True)
def _(M, mo, tabela, time):
    _linhas = []
    for _n in (4, 8, 16, 32, 64):
        for _restr in (False, True):
            _sf = M.MultiplicacaoSFOTS(_n, restringir_entradas=_restr)
            _t0 = time.perf_counter()
            _r = M.animacao(_sf, timeout_ms=120_000)
            _dt = time.perf_counter() - _t0
            _ok = all(v == "unsat" for v in _r.values())
            _linhas.append([_n, "a,b < 2^(n/2)" if _restr else "quaisquer", _r["parado_indutivo"], _r["T_total"],
                            _r["Pestrela_indutivo"], _r["Pestrela_inicial"], f"{_dt:.2f}", "sim" if _ok else "não provado"])
    mo.vstack([
        mo.md(tabela(["n", "entradas", "1. parado indutivo", "2. T total", "3. P* indutivo", "4. P* inicial", "tempo (s)", "F parado"], _linhas)),
        mo.callout(mo.md(
            "Conclusão: as quatro condições são `unsat`, logo o programa termina sempre, para quaisquer $a$ e $b$, "
            "mesmo com $n=64$ bits. Esta prova só usa somas, comparações e deslocamentos, por isso escala bem."),
            kind="success"),
    ])
    return


@app.cell(hide_code=True)
def _(M, Not, mo, tabela):
    _linhas = []
    for _n in (4, 6, 8):
        _sf = M.MultiplicacaoSFOTS(_n)
        _ativo = lambda s, _sf=_sf: Not(_sf.parado(s))
        _a = M.bmc_alcanca(_sf, _ativo, K=2 * _n - 1, exato=True)[0]
        _b = M.bmc_alcanca(_sf, _ativo, K=2 * _n, exato=True)[0]
        _m = max(M.referencia(a, b, _n)[4] for a in range(2 ** _n) for b in range(2 ** _n)) if _n <= 6 else "-"
        _linhas.append([_n, _a, _b, _m])
    mo.md(
        "### 5.5 Quantos passos?\n\n"
        "Em cada volta $y$ perde um bit (ramo par) ou passa a par (ramo ímpar), pelo que o programa pára em, no máximo, "
        "$2n$ transições. O BMC mostra que o limite é exato: existe um traço ainda ativo com $2n-1$ transições e nenhum com $2n$.\n\n"
        + tabela(["n", "traço ativo após 2n−1 passos?", "traço ativo após 2n passos?", "máximo de passos (simulador)"], _linhas)
    )
    return


@app.cell(hide_code=True)
def _(M, mo, tabela):
    _linhas = []
    for _n in (4, 6, 8, 10):
        _com = M.MultiplicacaoSFOTS(_n, restringir_entradas=True)
        _sem = M.MultiplicacaoSFOTS(_n)
        _nao_stop = lambda s: s.pc != M.STOP
        _linhas.append([_n, M.bmc_alcanca(_com, _nao_stop, K=2 * _n, exato=True)[0], M.bmc_alcanca(_sem, _nao_stop, K=2 * _n, exato=True)[0]])
    mo.vstack([
        mo.md(
            "### 5.6 Terminar em `STOP`\n\n"
            "Pergunta ao solver: ao fim de $2n$ transições, é possível não estar em `STOP`?\n\n"
            + tabela(["n", "com a,b < 2^(n/2)", "com a,b quaisquer"], _linhas)
        ),
        mo.callout(mo.md(
            "Conclusão: com a restrição a resposta é `unsat`, e o programa pára sempre em `STOP`. Sem ela é `sat`, porque pode parar em `ERROR`. "
            "Isto é coerente com o §4 e justifica entender «termina» como «pára» no caso geral."), kind="success"),
    ])
    return


@app.cell(hide_code=True)
def _(M, T, codigo, mo):
    _texto = mo.md(r"""
    ---
    ## 6. Validação: correção, eficiência e escala

    ### 6.1 Correção: testes com `pytest`
    Os testes (`test_sfots_mult.py`) estão em quatro grupos:

    | Grupo | O que garante |
    |:--|:--|
    | Modelo e programa | a transição Z3 coincide com o simulador em Python (estados arbitrários, execuções completas, overflow); $T$ é determinística e total |
    | Provas | invariante $1$-indutivo; $Q$ $1$-indutiva; as quatro condições da animação; limite exato de $2n$ passos; `F STOP` com restrição; PDR |
    | Controlos negativos | invariante falso recusado; $P$ sozinho não é $k$-indutivo; sem restrição o erro é acessível e o contra-exemplo confirma-se no simulador |
    | Verificação independente | força bruta em Python puro, sem Z3: sobre todos os estados, o invariante é indutivo ($n=3$), $Q$ é indutiva e $P$ não ($n=4$), e $R$ desce ($n=3$); sobre todos os pares $(a,b)$ nunca há `ERROR` com $a,b<2^{n/2}$ ($n=4,6,8$) |

    Dois exemplos, um de cada tipo (o primeiro compara o Z3 com o simulador, o segundo repete por enumeração o que o Z3 provou):
    """)
    mo.vstack([_texto, codigo(T.test_transicao_coincide_com_oraculo, T.test_exaustivo_reforco_Q_e_indutivo_e_P_sozinho_nao)])
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
def _(mo):
    mo.md(r"""
    ### 6.2 Eficiência

    As provas dos §3 e §4 contêm multiplicações entre incógnitas ($x\cdot y$, $a\cdot b$ e, em $2n$ bits, o dobro). O Z3 converte-as
    em circuitos com $O(n^2)$ portas, o que pesa muito no SAT. Como $T$ é uma disjunção de cinco ramos, pedir de uma vez a prova de
    $P\wedge T\wedge\neg P'$ obriga o solver a descobrir sozinho a análise por casos (par, ímpar, paragem).

    A otimização `dividir_ramos=True` explora que $A\wedge(T_1\vee\dots\vee T_5)\wedge\neg B$ é `unsat` se e só se cada
    $A\wedge T_i\wedge\neg B$ o for. A condição (b) da $k$-indução decompõe-se em $5^k$ problemas pequenos. É logicamente equivalente
    (os veredictos coincidem, o que está testado) e muito mais rápida. A animação (§5) não precisa disto.

    ### 6.3 Escala
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    executar = mo.ui.switch(value=False, label="Repetir a medição da tabela de escala neste computador (demora vários minutos)")
    executar
    return (executar,)


@app.cell(hide_code=True)
def _(M, executar, mo, tabela):
    _cab = ["n", "invariante: direto", "invariante: por ramos", "segurança Q: direto", "segurança Q: por ramos"]
    _ref = [
        [4, "0,04 s", "0,02 s", "0,02 s", "0,03 s"],
        [6, "0,24 s", "0,02 s", "0,11 s", "0,06 s"],
        [8, "3,6 s", "0,36 s", "0,56 s", "0,29 s"],
        [10, "34 s", "3,0 s", "2,8 s", "1,7 s"],
        [12, "timeout (120 s)", "2,2 s", "24 s", "7,2 s"],
        [16, "timeout (120 s)", "9,8 s ou timeout (200 s) *", "timeout (120 s)", "124 s"],
    ]
    if not executar.value:
        _saida = mo.md(
            "Tempos de referência (medidos antes, com Z3 5.3.3 em 2 vCPU; o interruptor acima repete a medição neste computador):\n\n"
            + tabela(_cab, _ref)
            + "\n\n\\* Para $n\\ge12$ o tempo depende da heurística do SAT: o mesmo problema, com variáveis de outros nomes, "
              "demorou 9,8 s numa execução e deu *timeout* noutra. O que se pode concluir é que decompor por ramos ganha uma a duas "
              "ordens de grandeza, não os valores exatos."
        )
    else:
        def _t(sf, P, div):
            r = M.k_inducao(sf, P, 1, timeout_ms=60_000, dividir_ramos=div)
            return f"{r.segundos:.2f} s" if r.provado else f"{r.veredicto} ({r.segundos:.0f} s)"
        _linhas = []
        for _n in (4, 6, 8, 10, 12):
            _a, _b = M.MultiplicacaoSFOTS(_n), M.MultiplicacaoSFOTS(_n, restringir_entradas=True)
            _linhas.append([_n, _t(_a, M.invariante_produto(_a), False), _t(_a, M.invariante_produto(_a), True),
                            _t(_b, M.seguranca_reforcada(_b), False), _t(_b, M.seguranca_reforcada(_b), True)])
        _saida = mo.md("Medições feitas agora (limite de 60 s por problema):\n\n" + tabela(_cab, _linhas))
    _saida
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ## 7. Conclusões

    | Ponto | Resultado | Técnica |
    |:--|:--|:--|
    | 3.1 SFOTS | $\langle X,I,T,E\rangle$ sobre `BitVec(n)`, com $T$ total e determinística, coincidente com o programa | Z3, pytest, simulador |
    | 3.2 invariante | $x\,y+z=a\,b$ é invariante ($1$-indutivo, também com overflow, módulo $2^n$) | $k$-indução, $k=1$ |
    | 3.3 segurança | duas provas: $\neg E$ sozinho é $k$-indutivo a partir de $k=2n$ (falha abaixo), e o reforço $Q$ ($2n$ bits e limites) é $1$-indutivo; em ambas o erro é inacessível com $a,b<2^{n/2}$; sem a restrição há contra-exemplo | $k$-indução, BMC (e PDR, extra) |
    | 3.4 animação | $F\,\text{parado}$ vale para todos os $a,b$ (e $F\,\text{STOP}$ com $a,b<2^{n/2}$); pára em $\le 2n$ passos, limite exato | *look-ahead* $P^*$ com ordem bem fundada, BMC |

    Limitações:

    * As provas por $k$-indução com multiplicações (§3 e §4) tornam-se lentas para $n\gtrsim12$ e dependem da heurística do SAT (§6.3). A animação não tem este problema.
    * O PDR (§4.6) só foi medido até $n=10$.
    * O invariante do §3 é módulo $2^n$. Só com $a,b<2^{n/2}$ coincide com o produto «verdadeiro», e é isso que o reforço $Q$ do §4 formaliza.
    * Os tempos de referência da §6.3 foram medidos numa máquina de 2 núcleos e variam de máquina para máquina.

    ## 8. Diálogo com ferramentas LLM

    Usámos o Claude (Anthropic) como assistente neste exercício: para discutir e perceber os conceitos da matéria (SFOTS, $k$-indução,
    propriedades de animação com *look-ahead*) e para ajudar a escrever o modelo em Z3, os testes e o texto deste notebook.
    O código foi executado e testado por nós (`pytest` e o próprio notebook).

    Conversa: https://claude.ai/share/e3763b6b-4da6-4d9f-b6b7-15947f457ce1

    ---
    ## Apêndice: como executar

    ```bash
    cd TP2
    python3 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cd ex3
    pytest                                                 # testes rápidos
    pytest -m slow                                         # testes de escala
    marimo edit ex3_multiplicacao.py --no-sandbox          # abrir o notebook
    marimo run  ex3_multiplicacao.py --no-sandbox          # só leitura
    marimo export html ex3_multiplicacao.py -o ex3.html    # exportar (depois imprimir para PDF)
    ```
    """)
    return


if __name__ == "__main__":
    app.run()
