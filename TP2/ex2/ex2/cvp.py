"""
Exercício 2 (TP2): Closest Vector Problem com programação cónica.

Dado o reticulado gerado pelas linhas de G (k vetores de R^m) e um alvo t,
procura-se z inteiro, com 0 <= z_i <= l, que minimiza  || G^T z - t ||_2.

A relaxação contínua (z real na caixa [0, l]^k) é um problema cónico de segunda
ordem (SOCP), resolvido com `cvxpy` e o solver Clarabel. Como o Clarabel não
trata variáveis inteiras, os inteiros são tratados por um branch-and-bound
escrito aqui (best-first, com ramificação em todos os valores inteiros).

Também há um resolvedor de apoio, com `scipy`, que resolve a mesma relaxação.
Serve só para conferir o Clarabel e para os testes quando o cvxpy não existe.
"""
from __future__ import annotations

import heapq
import itertools
import time
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import lsq_linear

TOL_PODA = 1e-6          # tolerância absoluta na distância para podar / declarar ótimo


# --------------------------------------------------------------------------
# 1. Instâncias
# --------------------------------------------------------------------------
@dataclass
class Instancia:
    """G tem uma linha por vetor da base (k x m); t = G^T u com u em [0, l]^k."""
    G: np.ndarray
    t: np.ndarray
    l: int
    u: np.ndarray
    semente: int
    sigma_min: float            # menor valor singular de G (mede se é mesmo uma base)

    @property
    def k(self) -> int:
        return self.G.shape[0]

    @property
    def m(self) -> int:
        return self.G.shape[1]

    @property
    def A(self) -> np.ndarray:
        """Matriz m x k cujas colunas são os vetores da base: x = A z."""
        return self.G.T


def verificar_base(G: np.ndarray) -> tuple[bool, float]:
    """Os k vetores (linhas de G) são linearmente independentes sse o menor valor singular é > 0."""
    sv = np.linalg.svd(G, compute_uv=False)
    tol = max(G.shape) * np.finfo(float).eps * sv[0]
    return bool(sv[-1] > tol), float(sv[-1])


def gerar_instancia(k: int, m: int, l: int, semente: int = 0) -> Instancia:
    """Gera G com entradas uniformes em [0,1] (repete se não for base) e t = G^T u."""
    if m < k:
        raise ValueError("é preciso m >= k para haver k vetores independentes em R^m")
    if l < 1:
        raise ValueError("l tem de ser um inteiro positivo")
    rng = np.random.default_rng(semente)
    while True:
        G = rng.random((k, m))
        ok, smin = verificar_base(G)
        if ok:
            break
    u = rng.uniform(0.0, l, size=k)
    return Instancia(G=G, t=G.T @ u, l=int(l), u=u, semente=semente, sigma_min=smin)


def distancia(inst: Instancia, z) -> float:
    return float(np.linalg.norm(inst.A @ np.asarray(z, dtype=float) - inst.t))


# --------------------------------------------------------------------------
# 2. Relaxação cónica
# --------------------------------------------------------------------------
def _relaxar_clarabel(A, t, l, mascara, valores):
    """min ||A z - t||_2  s.a.  0 <= z <= l nas variáveis livres (as outras estão fixas).

    É um SOCP: o objetivo é uma norma euclidiana (cone de segunda ordem).
    """
    import cvxpy as cp

    livres = np.flatnonzero(~mascara)
    t_ef = t - A[:, mascara] @ valores[mascara]
    z = cp.Variable(len(livres))
    problema = cp.Problem(cp.Minimize(cp.norm(A[:, livres] @ z - t_ef, 2)),
                          [z >= 0, z <= l])
    problema.solve(solver=cp.CLARABEL)
    if problema.status not in ("optimal", "optimal_inaccurate"):
        raise RuntimeError(f"Clarabel terminou com estado {problema.status}")
    x = valores.astype(float).copy()
    x[livres] = np.clip(z.value, 0, l)
    return float(problema.value), x


def _relaxar_scipy(A, t, l, mascara, valores):
    """Mesma relaxação, como mínimos quadrados com limites (resolvedor de apoio)."""
    livres = np.flatnonzero(~mascara)
    t_ef = t - A[:, mascara] @ valores[mascara]
    r = lsq_linear(A[:, livres], t_ef, bounds=(0.0, float(l)), method="bvls", tol=1e-12)
    x = valores.astype(float).copy()
    x[livres] = r.x
    return float(np.linalg.norm(A[:, livres] @ r.x - t_ef)), x


RELAXACOES = {"clarabel": _relaxar_clarabel, "scipy": _relaxar_scipy}


def cvxpy_disponivel() -> bool:
    try:
        import cvxpy as cp
        return "CLARABEL" in cp.installed_solvers()
    except Exception:
        return False


# --------------------------------------------------------------------------
# 3. Heurística primal: arredondar e melhorar coordenada a coordenada
# --------------------------------------------------------------------------
def melhoria_local(A, t, z, l):
    """Dado z inteiro em [0,l]^k, melhora-o mexendo numa coordenada de cada vez.

    Para a coordenada i, o melhor inteiro é o mais próximo de z_i + A_i.r / ||A_i||^2,
    com r = t - A z, truncado a [0, l]. Repete até nada melhorar.
    """
    z = z.astype(float).copy()
    r = t - A @ z
    norma2 = (A * A).sum(axis=0)
    melhorou = True
    while melhorou:
        melhorou = False
        for i in range(len(z)):
            novo = float(np.clip(np.round(z[i] + A[:, i] @ r / norma2[i]), 0, l))
            if novo != z[i]:
                r_novo = r - A[:, i] * (novo - z[i])
                if r_novo @ r_novo < r @ r - 1e-12:
                    z[i], r, melhorou = novo, r_novo, True
    return z


# --------------------------------------------------------------------------
# 4. Branch-and-bound
# --------------------------------------------------------------------------
@dataclass
class Resultado:
    z: np.ndarray                  # melhor solução inteira encontrada
    dist: float                    # a sua distância ao alvo (limite superior)
    limite_inf: float              # limite inferior da distância ótima
    otimo: bool                    # True se foi provado ótimo (dentro de TOL_PODA)
    nos: int                       # relaxações cónicas resolvidas
    podados: int                   # filhos eliminados pela poda barata, sem resolver a relaxação
    segundos: float
    motivo: str                    # "otimo", "tempo" ou "nos"
    evolucao: list = field(default_factory=list)   # (nós, melhor distância) a cada melhoria

    @property
    def folga(self) -> float:
        return self.dist - self.limite_inf


def _analise_livres(A, t_ef, livres):
    """Mínimos quadrados sem limites nas variáveis livres.

    Devolve (z_ls, r_ls, d): o ótimo sem caixa, a sua distância ao alvo e, para cada
    variável, a distância d_i da coluna i ao subespaço das outras colunas livres
    (d_i = 1/sqrt((Af^T Af)^-1_ii)). Fixar a variável i num valor a faz a distância
    ao quadrado subir exatamente ((a - z_ls_i) d_i)^2 em relação a r_ls^2.
    """
    Af = A[:, livres]
    P = np.linalg.inv(Af.T @ Af)
    z_ls = P @ (Af.T @ t_ef)
    r_ls = float(np.linalg.norm(Af @ z_ls - t_ef))
    return z_ls, r_ls, 1.0 / np.sqrt(np.diag(P))


def _escolher_variavel(x, livres, z_ls, d, regra):
    """Escolhe a variável livre onde ramificar (índice dentro de `livres`)."""
    frac = np.abs(x[livres] - np.round(x[livres]))
    if regra == "fracionaria":
        return int(np.argmax(frac))
    if regra == "indice":
        return 0
    if regra == "distancia":
        return int(np.argmax(d))
    # "perp": fixar a variável no inteiro mais próximo do ótimo contínuo faz a
    # distância subir pelo menos |frac_i| d_i; ramifica-se onde essa subida é maior.
    return int(np.argmax(d * frac))


def branch_and_bound(inst: Instancia, relaxacao: str = "clarabel", regra: str = "perp",
                     limite_s: float | None = None, limite_nos: int | None = None,
                     poda_barata: bool = True) -> Resultado:
    """Resolve o CVP da instância. Devolve o melhor z e, se acabar, a prova de otimalidade."""
    resolver = RELAXACOES[relaxacao]
    A, t, l, k = inst.A, inst.t, inst.l, inst.k
    t0 = time.perf_counter()

    # solução inicial: arredondar o ótimo contínuo e melhorar
    d_raiz, x_raiz = resolver(A, t, l, np.zeros(k, bool), np.zeros(k))
    nos = 1
    melhor = melhoria_local(A, t, np.clip(np.round(x_raiz), 0, l), l)
    d_melhor = float(np.linalg.norm(A @ melhor - t))
    evolucao = [(nos, d_melhor)]

    contador = itertools.count()
    # cada nó: (limite inferior herdado do pai, desempate, máscara dos fixos, valores fixos)
    fila = [(d_raiz, next(contador), np.zeros(k, bool), np.zeros(k), x_raiz)]
    motivo = "otimo"
    podados = 0
    while fila:
        lb_no, _, mascara, valores, x = fila[0]
        if lb_no >= d_melhor - TOL_PODA:
            fila.clear()
            break
        if limite_s is not None and time.perf_counter() - t0 > limite_s:
            motivo = "tempo"
            break
        if limite_nos is not None and nos >= limite_nos:
            motivo = "nos"
            break
        heapq.heappop(fila)

        livres = np.flatnonzero(~mascara)
        t_ef = t - A[:, mascara] @ valores[mascara]
        z_ls, r_ls, dperp = _analise_livres(A, t_ef, livres)
        j = _escolher_variavel(x, livres, z_ls, dperp, regra)
        i = int(livres[j])
        for a in range(l + 1):
            # poda barata: mesmo sem os limites 0 <= z <= l, fixar z_i = a obriga a
            # distância >= sqrt(r_ls^2 + ((a - z_ls_i) d_i)^2); se já não melhora, nem se resolve a relaxação
            if poda_barata and np.hypot(r_ls, (a - z_ls[j]) * dperp[j]) >= d_melhor - TOL_PODA:
                podados += 1
                continue
            m2, v2 = mascara.copy(), valores.copy()
            m2[i], v2[i] = True, a
            if m2.all():
                d, x2 = float(np.linalg.norm(A @ v2 - t)), v2.astype(float)
            else:
                d, x2 = resolver(A, t, l, m2, v2)
                nos += 1
            if d >= d_melhor - TOL_PODA:
                continue
            z = melhoria_local(A, t, np.clip(np.round(x2), 0, l), l)
            dz = float(np.linalg.norm(A @ z - t))
            if dz < d_melhor - 1e-12:
                melhor, d_melhor = z, dz
                evolucao.append((nos, d_melhor))
            if not m2.all():
                heapq.heappush(fila, (d, next(contador), m2, v2, x2))

    limite_inf = d_melhor if not fila else min(d_melhor, fila[0][0])
    return Resultado(z=melhor.astype(int), dist=d_melhor, limite_inf=limite_inf,
                     otimo=(motivo == "otimo"), nos=nos, podados=podados,
                     segundos=time.perf_counter() - t0, motivo=motivo, evolucao=evolucao)


# --------------------------------------------------------------------------
# 5. Verificadores independentes (sem cvxpy, sem relaxações)
# --------------------------------------------------------------------------
def forca_bruta(inst: Instancia, max_pontos: int = 3_000_000):
    """Testa todos os (l+1)^k vetores. Só para instâncias pequenas."""
    A, t, l, k = inst.A, inst.t, inst.l, inst.k
    total = (l + 1) ** k
    if total > max_pontos:
        raise ValueError(f"{total} pontos é demasiado para força bruta")
    melhor, d_melhor = None, np.inf
    lote = 200_000
    for ini in range(0, total, lote):
        idx = np.arange(ini, min(ini + lote, total))
        Z = np.empty((len(idx), k))
        for j in range(k):
            Z[:, j] = (idx // (l + 1) ** j) % (l + 1)
        d = np.linalg.norm(Z @ A.T - t, axis=1)
        p = int(np.argmin(d))
        if d[p] < d_melhor:
            melhor, d_melhor = Z[p].astype(int), float(d[p])
    return melhor, d_melhor


def esfera_exata(inst: Instancia, max_nos: int = 5_000_000):
    """Enumeração de Schnorr-Euchner sobre a decomposição QR (algoritmo exato clássico).

    Devolve (z, distância) ou (None, None) se ultrapassar `max_nos`.
    """
    A, t, l, k = inst.A, inst.t, inst.l, inst.k
    Q, R = np.linalg.qr(A)                    # A = Q R, R é k x k triangular superior
    tq = Q.T @ t
    resto2 = float(t @ t - tq @ tq)           # parte de t fora do subespaço gerado por A
    z0 = melhoria_local(A, t, np.clip(np.round(np.linalg.lstsq(A, t, rcond=None)[0]), 0, l), l)
    melhor = [z0.astype(int), float(np.linalg.norm(A @ z0 - t)) ** 2]
    z = np.zeros(k)
    nos = [0]

    def desce(i, parcial):
        nos[0] += 1
        if nos[0] > max_nos:
            raise OverflowError
        centro = (tq[i] - R[i, i + 1:] @ z[i + 1:]) / R[i, i]
        folga = melhor[1] - resto2 - parcial
        if folga < 0:
            return
        raio = np.sqrt(folga) / abs(R[i, i])
        candidatos = range(max(0, int(np.ceil(centro - raio))), min(l, int(np.floor(centro + raio))) + 1)
        for a in sorted(candidatos, key=lambda a: abs(a - centro)):
            z[i] = a
            p = parcial + (R[i, i] * (a - centro)) ** 2
            if p + resto2 >= melhor[1]:
                continue
            if i == 0:
                melhor[0], melhor[1] = z.astype(int).copy(), p + resto2
            else:
                desce(i - 1, p)
        z[i] = 0

    try:
        desce(k - 1, 0.0)
    except OverflowError:
        return None, None
    return melhor[0], float(np.sqrt(melhor[1]))
