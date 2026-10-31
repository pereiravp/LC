"""
Testes pytest do Exercício 3 (SFOTS da multiplicação).

Três tipos de teste:
  1. o modelo Z3 coincide com um oráculo em Python (`passo_ref`/`referencia`);
  2. as propriedades que devem ser provadas SÃO provadas (unsat);
  3. "controlos negativos": o que deve falhar, falha (e com o contra-exemplo certo).
Correr:  pytest -v          (os testes lentos:  pytest -m slow)
"""
import itertools
import random

import pytest
from z3 import And, BitVecVal, Not, Solver, sat, unsat

from sfots_mult import (
    DO, ERROR, STOP, MultiplicacaoSFOTS, animacao, bmc_alcanca, invariante_produto,
    iguais, k_inducao, passo_ref, referencia, seguranca_reforcada, seguranca_simples,
    pdr_erro_acessivel, traco_ref,
)

PCS = {"DO": DO, "STOP": STOP, "ERROR": ERROR}
NS = [4, 6, 8]


def fixa(s, pc, a, b, x, y, z, n):
    bv = lambda v: BitVecVal(v, n)
    return And(s.pc == PCS[pc], s.a == bv(a), s.b == bv(b),
               s.x == bv(x), s.y == bv(y), s.z == bv(z))


def lê(modelo, t):
    nome = {str(DO): "DO", str(STOP): "STOP", str(ERROR): "ERROR"}
    return (nome[str(modelo.eval(t.pc, model_completion=True))],
            *[modelo.eval(v, model_completion=True).as_long() for v in (t.a, t.b, t.x, t.y, t.z)])


# 1. o modelo Z3 == oráculo Python
@pytest.mark.parametrize("n", NS)
def test_transicao_coincide_com_oraculo(n):
    """Para estados ARBITRÁRIOS (também os não acessíveis) T tem exatamente
    um sucessor e é o que o programa em Python calcula."""
    sf = MultiplicacaoSFOTS(n)
    rnd = random.Random(2026 + n)
    s, t = sf.estado("s"), sf.estado("t")
    for _ in range(60):
        pc = rnd.choice(["DO", "DO", "DO", "STOP", "ERROR"])
        a, b, x, y, z = (rnd.randrange(2 ** n) for _ in range(5))
        solver = Solver()
        solver.add(fixa(s, pc, a, b, x, y, z, n), sf.trans(s, t))
        assert solver.check() == sat
        obtido = lê(solver.model(), t)
        assert obtido == passo_ref(pc, a, b, x, y, z, n), (pc, a, b, x, y, z)
        # unicidade do sucessor
        modelo = solver.model()
        solver.add(Not(And(*[u == modelo.eval(u, model_completion=True) for u in t.todas()])))
        assert solver.check() == unsat


@pytest.mark.parametrize("n", NS)
def test_execucao_z3_coincide_com_referencia(n):
    """Iterando T a partir de I (a, b concretos) obtém-se o mesmo estado final
    e o mesmo nº de passos que no oráculo."""
    sf = MultiplicacaoSFOTS(n)
    rnd = random.Random(7 * n)
    for _ in range(15):
        a, b = rnd.randrange(2 ** n), rnd.randrange(2 ** n)
        atual = ("DO", a, b, a, b, 0)
        passos = 0
        s, t = sf.estado("s"), sf.estado("t")
        while atual[0] == "DO":
            solver = Solver()
            solver.add(fixa(s, *atual, n), sf.trans(s, t))
            assert solver.check() == sat
            atual = lê(solver.model(), t)
            passos += 1
        pc_ref, x_ref, y_ref, z_ref, passos_ref = referencia(a, b, n)
        assert (atual[0], atual[3], atual[4], atual[5], passos) == (pc_ref, x_ref, y_ref, z_ref, passos_ref)


@pytest.mark.parametrize("n", [4, 5, 6])
def test_programa_calcula_o_produto_ou_da_erro(n):
    """Oráculo: ou pára em STOP com z = a*b, ou dá ERROR por overflow."""
    for a, b in itertools.product(range(2 ** n), repeat=2):
        pc, _, y, z, _ = referencia(a, b, n)
        if pc == "STOP":
            assert y == 0 and z == a * b
        else:
            assert pc == "ERROR"


def test_oraculo_overflow_concreto():
    assert referencia(15, 15, 8)[:4:3] == ("STOP", 225)          # a,b < 2^4: sem erro
    assert referencia(16, 16, 8)[0] == "ERROR"                   # 256 não cabe em 8 bits
    assert referencia(255, 255, 8)[0] == "ERROR"


# 2. propriedades que têm de ser provadas
@pytest.mark.parametrize("n", NS)
def test_transicao_total_e_deterministica(n):
    sf = MultiplicacaoSFOTS(n)
    assert animacao(sf)["T_total"] == "unsat"
    s, t1, t2 = sf.estado("s"), sf.estado("t1"), sf.estado("t2")
    solver = Solver()
    solver.add(sf.trans(s, t1), sf.trans(s, t2), Not(iguais(t1, t2)))
    assert solver.check() == unsat


@pytest.mark.parametrize("n", NS)
def test_ponto2_invariante_produto_e_1_indutivo(n):
    r = k_inducao(MultiplicacaoSFOTS(n), invariante_produto(None), k=1)
    assert r.provado, r


@pytest.mark.parametrize("n", [4, 6, 8])
def test_ponto3_seguranca_reforcada_e_1_indutiva(n):
    sf = MultiplicacaoSFOTS(n, restringir_entradas=True)
    r = k_inducao(sf, seguranca_reforcada(sf), k=1)
    assert r.provado, r


@pytest.mark.parametrize("n", [4, 6])
def test_reforco_implica_seguranca(n):
    sf = MultiplicacaoSFOTS(n, restringir_entradas=True)
    s = sf.estado("s")
    solver = Solver()
    solver.add(seguranca_reforcada(sf)(s), Not(seguranca_simples(sf)(s)))
    assert solver.check() == unsat


@pytest.mark.parametrize("n", [4, 6])
def test_ponto3_sem_erro_acessivel_por_bmc(n):
    sf = MultiplicacaoSFOTS(n, restringir_entradas=True)
    veredicto, _ = bmc_alcanca(sf, sf.erro, K=2 * n + 2)
    assert veredicto == "unsat"


@pytest.mark.parametrize("n", [4, 6, 8])
@pytest.mark.parametrize("restringir", [False, True])
def test_ponto4_animacao(n, restringir):
    """Σ ⊨ F parado, para quaisquer a, b (e também com a, b < 2^(n/2))."""
    sf = MultiplicacaoSFOTS(n, restringir_entradas=restringir)
    assert set(animacao(sf).values()) == {"unsat"}


@pytest.mark.parametrize("n", [4, 6, 8])
def test_ponto4_limite_de_passos_e_justo(n):
    """Todos os traços estão parados ao fim de 2n transições; e existe um
    traço ainda ativo com 2n-1 (o limite é justo)."""
    sf = MultiplicacaoSFOTS(n)
    ativo = lambda s: Not(sf.parado(s))
    assert bmc_alcanca(sf, ativo, K=2 * n, exato=True)[0] == "unsat"
    assert bmc_alcanca(sf, ativo, K=2 * n - 1, exato=True)[0] == "sat"


@pytest.mark.parametrize("n", [4, 5, 6])
def test_limite_de_passos_coincide_com_oraculo(n):
    maximo = max(referencia(a, b, n)[4] for a in range(2 ** n) for b in range(2 ** n))
    assert maximo == 2 * n


# 3. controlos negativos (o que deve falhar, falha)
def test_invariante_errado_e_refutado_na_base():
    sf = MultiplicacaoSFOTS(6)
    errado = lambda s: s.x * s.y + s.z == s.a * s.b + 1
    r = k_inducao(sf, errado, k=1)
    assert not r.provado and r.falha == "base j=0" and r.contra_exemplo


def test_seguranca_simples_nao_e_k_indutiva():
    """P ≡ ¬erro sozinho não é k-indutivo (para nenhum k pequeno): há estados
    arbitrários não acessíveis (ex.: x enorme) cujo sucessor é error."""
    sf = MultiplicacaoSFOTS(6, restringir_entradas=True)
    for k in range(1, 6):
        r = k_inducao(sf, seguranca_simples(sf), k=k)
        assert not r.provado and r.falha == "passo", k
        assert r.contra_exemplo[-1]["pc"] == "ERROR"


@pytest.mark.parametrize("n", [4, 6, 8])
def test_sem_restricao_o_erro_e_acessivel(n):
    """Sem a < 2^(n/2) ∧ b < 2^(n/2) o programa pode dar overflow, e o
    contra-exemplo do BMC confirma-se no oráculo."""
    sf = MultiplicacaoSFOTS(n)
    veredicto, traco = bmc_alcanca(sf, sf.erro, K=2 * n)
    assert veredicto == "sat"
    a, b = traco[0]["a"], traco[0]["b"]
    assert referencia(a, b, n)[0] == "ERROR"
    r = k_inducao(sf, seguranca_simples(sf), k=2 * n)
    assert not r.provado and r.falha.startswith("base")


def test_mesmo_reforcado_falha_sem_restricao():
    sf = MultiplicacaoSFOTS(6, restringir_entradas=False)
    q = lambda s: And(Not(sf.erro(s)), sf.produto_largo(s) == sf.ab_largo(s))
    assert not k_inducao(sf, q, k=1).provado


# 3b. a otimização "dividir_ramos" não muda nenhum veredicto
@pytest.mark.parametrize("n", [4, 6])
def test_dividir_ramos_equivale_ao_direto(n):
    sf = MultiplicacaoSFOTS(n, restringir_entradas=True)
    casos = [
        (invariante_produto(sf), 1),                 # provado
        (seguranca_reforcada(sf), 1),                # provado
        (seguranca_simples(sf), 1),                  # passo falha
        (seguranca_simples(sf), 3),                  # passo falha
        (lambda s: s.x * s.y + s.z == s.a * s.b + 1, 1),   # base falha
    ]
    for P, k in casos:
        d = k_inducao(sf, P, k)
        r = k_inducao(sf, P, k, dividir_ramos=True)
        assert (d.provado, d.base_ok, d.passo_ok) == (r.provado, r.base_ok, r.passo_ok)


# 3c. F STOP direto e verificação EXAUSTIVA independente do Z3
#     (Python puro: enumera TODOS os estados de n pequeno e confirma, por
#      força bruta, o que o Z3 provou simbolicamente)
@pytest.mark.parametrize("n", [4, 6, 8])
def test_com_restricao_termina_sempre_em_stop(n):
    """F STOP (e não apenas F parado) quando a, b < 2^(n/2): ao fim de 2n
    transições está-se sempre em STOP. Sem a restrição isso é falso."""
    com = MultiplicacaoSFOTS(n, restringir_entradas=True)
    assert bmc_alcanca(com, lambda s: s.pc != STOP, K=2 * n, exato=True)[0] == "unsat"
    sem = MultiplicacaoSFOTS(n)
    assert bmc_alcanca(sem, lambda s: s.pc != STOP, K=2 * n, exato=True)[0] == "sat"


def _todos_os_estados(n, limite_ab):
    r = range(2 ** n)
    for a in range(limite_ab):
        for b in range(limite_ab):
            for x, y, z in itertools.product(r, repeat=3):
                for pc in ("DO", "STOP", "ERROR"):
                    yield pc, a, b, x, y, z


def test_exaustivo_invariante_e_1_indutivo():
    """n=3, TODOS os estados (também os inacessíveis): se x*y+z ≡ a*b (mod 2^n)
    então o sucessor também satisfaz."""
    n, m = 3, 2 ** 3
    for pc, a, b, x, y, z in _todos_os_estados(n, m):
        if (x * y + z) % m == (a * b) % m:
            _, a2, b2, x2, y2, z2 = passo_ref(pc, a, b, x, y, z, n)
            assert (x2 * y2 + z2) % m == (a2 * b2) % m, (pc, a, b, x, y, z)


def test_exaustivo_reforco_Q_e_indutivo_e_P_sozinho_nao():
    """n=4 com a,b < 4: Q é fechado para a transição; P=¬erro sozinho não é."""
    n = 4
    Q = lambda pc, a, b, x, y, z: pc != "ERROR" and x * y + z == a * b   # a,b<4 por construção
    p_sozinho_falha = False
    for e in _todos_os_estados(n, 2 ** (n // 2)):
        suc = passo_ref(*e, n)
        if Q(*e):
            assert Q(*suc), e                      # Q é indutivo
        if e[0] != "ERROR" and suc[0] == "ERROR":
            p_sozinho_falha = True                # existe passo P -> ¬P
    assert p_sozinho_falha


@pytest.mark.parametrize("n", [4, 6, 8])
def test_exaustivo_acessibilidade(n):
    """Todos os pares (a, b): com a,b < 2^(n/2) nunca há ERROR; e o programa calcula a*b."""
    lim = 2 ** (n // 2)
    for a in range(lim):
        for b in range(lim):
            pc, _, _, z, _ = referencia(a, b, n)
            assert pc == "STOP" and z == a * b
    assert any(referencia(a, b, n)[0] == "ERROR" for a in range(2 ** n) for b in range(2 ** n))


def test_exaustivo_animacao_medida_decresce():
    """n=3, TODOS os estados: fora dos estados parados a medida R=2y+[pc=DO]
    decresce estritamente; nos parados o estado repete-se."""
    n = 3
    R = lambda pc, y: 2 * y + (1 if pc == "DO" else 0)
    for pc, a, b, x, y, z in _todos_os_estados(n, 2 ** n):
        suc = passo_ref(pc, a, b, x, y, z, n)
        if pc == "DO":
            assert R(suc[0], suc[4]) < R(pc, y), (pc, a, b, x, y, z)
        else:
            assert suc == (pc, a, b, x, y, z)


@pytest.mark.parametrize("n", [3, 8])
def test_traco_ref_termina_dentro_do_limite(n):
    for a, b in [(0, 0), (1, 2 ** n - 1), (2 ** n - 1, 1), (3, 5)]:
        percurso = traco_ref(a, b, n)
        assert percurso[-1][0] in ("STOP", "ERROR") and len(percurso) - 1 <= 2 * n


# 3d. extra: o PDR (Spacer) chega à mesma conclusão sem o reforço manual
@pytest.mark.parametrize("n", [4, 6])
def test_pdr_conclui_o_mesmo_que_a_k_inducao(n):
    assert pdr_erro_acessivel(MultiplicacaoSFOTS(n, restringir_entradas=True)) == "unsat"
    assert pdr_erro_acessivel(MultiplicacaoSFOTS(n)) == "sat"


# 4. escala (lento)
@pytest.mark.slow
def test_escala_n12_inducao_por_ramos():
    sf = MultiplicacaoSFOTS(12, restringir_entradas=True)
    assert k_inducao(sf, invariante_produto(sf), k=1, timeout_ms=600_000, dividir_ramos=True).provado
    assert k_inducao(sf, seguranca_reforcada(sf), k=1, timeout_ms=600_000, dividir_ramos=True).provado


@pytest.mark.slow
@pytest.mark.parametrize("n", [12, 16, 24, 32])
def test_escala_animacao_n_grande(n):
    """A prova da animação não usa multiplicações: escala bem."""
    sf = MultiplicacaoSFOTS(n, restringir_entradas=True)
    assert set(animacao(sf).values()) == {"unsat"}


@pytest.mark.parametrize("n", [4, 6, 8])
def test_ponto3_seguranca_simples_e_k_indutiva_a_partir_de_2n(n):
    sf = MultiplicacaoSFOTS(n, restringir_entradas=True)
    abaixo = k_inducao(sf, seguranca_simples(sf), k=2 * n - 1)
    em_2n = k_inducao(sf, seguranca_simples(sf), k=2 * n)
    assert not abaixo.provado
    assert em_2n.provado
