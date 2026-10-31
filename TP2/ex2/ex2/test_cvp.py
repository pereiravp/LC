"""Testes do Exercício 2 (CVP com programação cónica).

Os resultados do branch-and-bound são sempre comparados com métodos que não
usam relaxações: força bruta (todos os pontos) e enumeração exata por esfera.
Os testes marcados com `com_cvxpy` correm o Clarabel a sério e são ignorados
se o cvxpy não estiver instalado.
"""
import numpy as np
import pytest

import cvp
from cvp import (Instancia, branch_and_bound, esfera_exata, forca_bruta,
                 gerar_instancia, melhoria_local, verificar_base)

com_cvxpy = pytest.mark.skipif(not cvp.cvxpy_disponivel(), reason="cvxpy/Clarabel não instalados")
SOLVERS = ["scipy"] + (["clarabel"] if cvp.cvxpy_disponivel() else [])

PEQUENAS = [(k, l, s) for k, l in [(3, 1), (4, 1), (5, 2), (6, 1), (4, 3), (5, 5)] for s in range(3)]


# ----------------------------------------------------------------- instâncias
@pytest.mark.parametrize("k,m,l", [(30, 60, 1), (40, 80, 5), (50, 100, 5)])
def test_instancia_cumpre_o_enunciado(k, m, l):
    inst = gerar_instancia(k, m, l, semente=7)
    assert inst.G.shape == (k, m)
    assert inst.G.min() >= 0 and inst.G.max() <= 1                  # probabilidades
    assert np.linalg.matrix_rank(inst.G) == k                       # é mesmo uma base
    assert inst.sigma_min > 0
    assert inst.u.min() >= 0 and inst.u.max() <= l
    assert np.allclose(inst.t, inst.G.T @ inst.u)                   # t = G^T u
    assert (inst.t > 0).all()                                       # t em R^m_+


def test_mesma_semente_mesma_instancia_e_sementes_diferentes_diferem():
    a, b, c = gerar_instancia(5, 10, 2, 1), gerar_instancia(5, 10, 2, 1), gerar_instancia(5, 10, 2, 2)
    assert np.array_equal(a.G, b.G) and np.array_equal(a.t, b.t)
    assert not np.array_equal(a.G, c.G)


def test_verificar_base_deteta_vetores_dependentes():
    rng = np.random.default_rng(0)
    G = rng.random((4, 8))
    assert verificar_base(G)[0]
    G[3] = 0.5 * G[0] + 0.25 * G[1]                                 # quarto vetor dependente
    assert not verificar_base(G)[0]
    G[3] = G[0]
    assert not verificar_base(G)[0]


def test_gerar_instancia_rejeita_parametros_invalidos():
    with pytest.raises(ValueError):
        gerar_instancia(5, 4, 1)                                    # m < k: não há base
    with pytest.raises(ValueError):
        gerar_instancia(5, 10, 0)                                   # l tem de ser positivo


# ------------------------------------------------------------------ relaxação
@com_cvxpy
@pytest.mark.parametrize("k,l", [(6, 1), (10, 5), (20, 5)])
def test_relaxacao_clarabel_coincide_com_o_resolvedor_de_apoio(k, l):
    inst = gerar_instancia(k, 2 * k, l, 3)
    rng = np.random.default_rng(1)
    for _ in range(4):
        mascara = rng.random(k) < 0.4
        valores = np.where(mascara, rng.integers(0, l + 1, k), 0)
        d1, x1 = cvp._relaxar_clarabel(inst.A, inst.t, l, mascara, valores)
        d2, x2 = cvp._relaxar_scipy(inst.A, inst.t, l, mascara, valores)
        assert d1 == pytest.approx(d2, abs=1e-5)
        assert np.allclose(x1[mascara], valores[mascara])           # fixos respeitados


@pytest.mark.parametrize("k,l,s", PEQUENAS)
def test_relaxacao_e_limite_inferior_do_otimo_inteiro(k, l, s):
    inst = gerar_instancia(k, 2 * k, l, s)
    d_rel, x = cvp._relaxar_scipy(inst.A, inst.t, l, np.zeros(k, bool), np.zeros(k))
    assert d_rel <= forca_bruta(inst)[1] + 1e-9
    assert d_rel < 1e-6                     # t = G^T u com u na caixa: o ótimo contínuo é u
    assert np.allclose(x, inst.u, atol=1e-6)


# ------------------------------------------------------------ branch-and-bound
@pytest.mark.parametrize("solver", SOLVERS)
@pytest.mark.parametrize("k,l,s", PEQUENAS)
def test_bb_coincide_com_a_forca_bruta(solver, k, l, s):
    inst = gerar_instancia(k, 2 * k, l, s)
    z_fb, d_fb = forca_bruta(inst)
    r = branch_and_bound(inst, solver)
    assert r.otimo and r.motivo == "otimo"
    assert r.dist == pytest.approx(d_fb, abs=1e-9)
    assert cvp.distancia(inst, r.z) == pytest.approx(r.dist, abs=1e-9)
    assert r.z.min() >= 0 and r.z.max() <= l                        # solução admissível
    assert r.limite_inf == pytest.approx(r.dist, abs=1e-6)


@pytest.mark.parametrize("k,l,s", PEQUENAS)
def test_esfera_exata_coincide_com_a_forca_bruta(k, l, s):
    inst = gerar_instancia(k, 2 * k, l, s)
    z, d = esfera_exata(inst)
    assert d == pytest.approx(forca_bruta(inst)[1], abs=1e-9)
    assert cvp.distancia(inst, z) == pytest.approx(d, abs=1e-9)


@pytest.mark.parametrize("regra", ["perp", "fracionaria", "indice", "distancia"])
def test_todas_as_regras_de_ramificacao_chegam_ao_mesmo_otimo(regra):
    inst = gerar_instancia(7, 14, 2, 4)
    assert branch_and_bound(inst, "scipy", regra).dist == pytest.approx(forca_bruta(inst)[1], abs=1e-9)


@pytest.mark.parametrize("k,l", [(12, 1), (15, 5), (20, 1), (20, 5)])
def test_bb_coincide_com_a_esfera_exata_em_instancias_medias(k, l):
    inst = gerar_instancia(k, 2 * k, l, 1)
    r = branch_and_bound(inst, "scipy")
    assert r.otimo and r.dist == pytest.approx(esfera_exata(inst)[1], abs=1e-6)


def test_bb_com_limite_de_nos_devolve_limites_coerentes():
    inst = gerar_instancia(14, 28, 5, 2)
    exato = esfera_exata(inst)[1]
    r = branch_and_bound(inst, "scipy", limite_nos=40)
    assert not r.otimo and r.motivo == "nos"
    assert r.limite_inf <= exato + 1e-6                             # limite inferior válido
    assert r.dist >= exato - 1e-9                                   # limite superior válido
    assert r.folga >= 0


def test_bb_com_limite_de_tempo_para():
    inst = gerar_instancia(40, 80, 5, 1)
    r = branch_and_bound(inst, "scipy", limite_s=0.3)
    assert not r.otimo and r.motivo == "tempo"
    assert r.limite_inf <= r.dist and r.segundos < 5


def test_evolucao_da_melhor_solucao_so_desce():
    inst = gerar_instancia(20, 40, 5, 5)
    ds = [d for _, d in branch_and_bound(inst, "scipy").evolucao]
    assert all(b < a for a, b in zip(ds, ds[1:]))


def test_poda_barata_so_elimina_filhos_que_nao_melhoram():
    """Com a poda ativa o ótimo é igual ao da esfera exata e há filhos podados."""
    inst = gerar_instancia(20, 40, 5, 1)
    r = branch_and_bound(inst, "scipy")
    assert r.podados > 0 and r.dist == pytest.approx(esfera_exata(inst)[1], abs=1e-6)


# ------------------------------------------------------------- heurística local
@pytest.mark.parametrize("s", range(5))
def test_melhoria_local_nunca_piora_e_fica_admissivel(s):
    inst = gerar_instancia(12, 24, 5, s)
    rng = np.random.default_rng(s)
    z0 = rng.integers(0, 6, 12).astype(float)
    z1 = melhoria_local(inst.A, inst.t, z0, 5)
    assert cvp.distancia(inst, z1) <= cvp.distancia(inst, z0) + 1e-12
    assert z1.min() >= 0 and z1.max() <= 5 and np.array_equal(z1, np.round(z1))


# --------------------------------------------------------------- casos limite
def test_k_igual_a_m_e_l_1():
    inst = gerar_instancia(5, 5, 1, 0)
    assert branch_and_bound(inst, "scipy").dist == pytest.approx(forca_bruta(inst)[1], abs=1e-9)


def test_alvo_dentro_do_reticulado_da_distancia_zero():
    base = gerar_instancia(6, 12, 3, 0)
    z = np.array([0, 3, 1, 2, 3, 0])
    inst = Instancia(G=base.G, t=base.A @ z, l=3, u=z.astype(float), semente=0, sigma_min=base.sigma_min)
    r = branch_and_bound(inst, "scipy")
    assert r.dist < 1e-9 and np.array_equal(r.z, z)


# ------------------------------------------------------------------------ lentos
@pytest.mark.slow
@pytest.mark.parametrize("k,l", [(30, 1), (30, 5)])
def test_escala_k30_resolvedor_de_apoio_contra_esfera(k, l):
    inst = gerar_instancia(k, 2 * k, l, 1)
    r = branch_and_bound(inst, "scipy")
    assert r.otimo and r.dist == pytest.approx(esfera_exata(inst)[1], abs=1e-6)


@pytest.mark.slow
@com_cvxpy
@pytest.mark.parametrize("k,l", [(15, 1), (15, 5)])
def test_escala_clarabel_k15_contra_esfera(k, l):
    inst = gerar_instancia(k, 2 * k, l, 1)
    r = branch_and_bound(inst, "clarabel")
    assert r.otimo and r.dist == pytest.approx(esfera_exata(inst)[1], abs=1e-5)


def test_sem_poda_barata_o_otimo_e_o_mesmo_mas_ha_mais_relaxacoes():
    inst = gerar_instancia(12, 24, 5, 1)
    com = branch_and_bound(inst, "scipy", poda_barata=True)
    sem = branch_and_bound(inst, "scipy", poda_barata=False)
    assert com.dist == pytest.approx(sem.dist, abs=1e-9) and sem.otimo
    assert sem.nos > com.nos and sem.podados == 0
