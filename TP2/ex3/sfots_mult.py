"""
Exercício 3 (TP2): SFOTS da multiplicação de inteiros com BitVec's de n bits.

O programa (Capítulo 4, parte 2, "Multiplicação de inteiros com erros") é

    x, y, z = a, b, 0
    while y != 0:
        if y é par:  x = 2*x ; y = y // 2        # ramo "even"
        else:        z = z + x ; y = y - 1       # ramo "odd"
        (se houve "overflow" -> local error)
    stop

Neste módulo:
  * `MultiplicacaoSFOTS` : o SFOTS (variáveis, estado inicial, transição, erro);
  * `k_inducao`          : verificação de G P por k-indução (condições (a) e (b) do Cap. 3);
  * `bmc_alcanca`        : BMC para obter contra-exemplos (traços até um alvo);
  * `animacao`           : prova de F "paragem" com o predicado "look ahead" P*;
  * `referencia`         : simulação em Python puro, usada como oráculo nos testes.
"""
from __future__ import annotations

import itertools
import time
from dataclasses import dataclass, field

from z3 import (
    And, BitVecs, BitVecVal, BoolSort, BVAddNoOverflow, Const, EnumSort, Extract,
    Fixedpoint, Function, If, Implies, LShR, Not, Or, Solver, Z3Exception, ULT, ZeroExt,
    sat, unknown, unsat,
)

# 1. Espaço de estados
# "program counter" com 3 locais. Os locais `even` e `odd` do CFA não têm
# comportamento próprio para além da atribuição, por isso são fundidos na
# transição que parte de DO (ver relatório). `error` é um local do pc.
PC, (DO, STOP, ERROR) = EnumSort("PC", ["DO", "STOP", "ERROR"])


@dataclass(frozen=True)
class Estado:
    """Um "clone" das variáveis de estado X = (pc, a, b, x, y, z)."""
    pc: object
    a: object
    b: object
    x: object
    y: object
    z: object

    def todas(self):
        return [self.pc, self.a, self.b, self.x, self.y, self.z]


def novo_estado(n: int, tag) -> Estado:
    """Cria um clone (variáveis frescas, nomeadas com `tag`) de X."""
    a, b, x, y, z = BitVecs(f"a@{tag} b@{tag} x@{tag} y@{tag} z@{tag}", n)
    return Estado(Const(f"pc@{tag}", PC), a, b, x, y, z)


def iguais(s: Estado, t: Estado):
    return And([u == v for u, v in zip(s.todas(), t.todas())])


# 2. O SFOTS  <BV_n, X, I, T, E>
class MultiplicacaoSFOTS:
    """SFOTS da multiplicação. `restringir_entradas=True` acrescenta ao estado
    inicial a condição (a < 2^(n/2)) ∧ (b < 2^(n/2)) do ponto 3 do enunciado."""

    def __init__(self, n: int, restringir_entradas: bool = False):
        if n < 2:
            raise ValueError("n >= 2")
        if restringir_entradas and n % 2:
            raise ValueError("para restringir as entradas n tem de ser par")
        self.n = n
        self.restringir_entradas = restringir_entradas

    # -- variáveis
    def estado(self, tag) -> Estado:
        return novo_estado(self.n, tag)

    def _bv(self, valor: int):
        return BitVecVal(valor, self.n)

    # -- predicado dos estados iniciais I
    def init(self, s: Estado):
        # Resultado de  havoc(a, b)  seguido da guarda (x=a) ∧ (y=b) ∧ (z=0)
        # (a e b arbitrários: ficam livres)
        I = And(s.pc == DO, s.x == s.a, s.y == s.b, s.z == self._bv(0))
        if self.restringir_entradas:
            limite = self._bv(2 ** (self.n // 2))
            I = And(I, ULT(s.a, limite), ULT(s.b, limite))
        return I

    # -- predicado de erro E
    def erro(self, s: Estado):
        return s.pc == ERROR

    # -- estados de paragem (terminais): STOP ou ERROR
    def parado(self, s: Estado):
        return Or(s.pc == STOP, s.pc == ERROR)

    # -- relação de transição T
    def _par(self, v):
        return Extract(0, 0, v) == 0  # bit menos significativo a 0

    def guardas(self, s: Estado) -> dict:
        """Guardas (switches) dos 5 ramos; cobrem todos os valores do pc."""
        zero = self._bv(0)
        return {
            "stop":   And(s.pc == DO, s.y == zero),
            "even":   And(s.pc == DO, s.y != zero, self._par(s.y)),
            "odd":    And(s.pc == DO, Not(self._par(s.y))),
            "sink_s": s.pc == STOP,
            "sink_e": s.pc == ERROR,
        }

    def ramos(self, s: Estado, t: Estado) -> dict:
        n = self.n
        g = self.guardas(s)
        # overflow da duplicação x -> 2x : perde-se o bit mais significativo
        ov_even = Extract(n - 1, n - 1, s.x) == 1
        # overflow da soma z + x (sem sinal)
        ov_odd = Not(BVAddNoOverflow(s.z, s.x, False))
        return {
            # y = 0 -> stop
            "stop": And(g["stop"], t.pc == STOP,
                        t.x == s.x, t.y == s.y, t.z == s.z),
            # y != 0 ∧ par(y):  x := 2x ; y := y/2  ; (overflow -> error, senão -> do)
            "even": And(g["even"], t.x == s.x << 1, t.y == LShR(s.y, 1),
                        t.z == s.z, t.pc == If(ov_even, ERROR, DO)),
            # y ímpar:  z := z + x ; y := y - 1  ; (overflow -> error, senão -> do)
            "odd": And(g["odd"], t.z == s.z + s.x, t.y == s.y - 1,
                       t.x == s.x, t.pc == If(ov_odd, ERROR, DO)),
            # stop e error são "sinks": o estado repete-se (a relação é total)
            "sink_s": And(g["sink_s"], iguais(s, t)),
            "sink_e": And(g["sink_e"], iguais(s, t)),
        }

    def trans(self, s: Estado, t: Estado):
        # a e b são constantes do programa (valores iniciais): nunca mudam
        return And(t.a == s.a, t.b == s.b, Or(list(self.ramos(s, t).values())))

    # -- predicados de apoio às propriedades
    def produto_largo(self, s: Estado):
        """x*y + z  calculado em 2n bits (sem perda por overflow)."""
        n = self.n
        return (ZeroExt(n, s.x) * ZeroExt(n, s.y)) + ZeroExt(n, s.z)

    def ab_largo(self, s: Estado):
        n = self.n
        return ZeroExt(n, s.a) * ZeroExt(n, s.b)

    def medida(self, s: Estado):
        """Medida bem fundada R(s) = 2*y + [pc = DO]  (em n+1 bits, sem overflow)."""
        n = self.n
        um = BitVecVal(1, n + 1)
        zero = BitVecVal(0, n + 1)
        return ZeroExt(1, s.y) * 2 + If(s.pc == DO, um, zero)


# 3. Propriedades
def invariante_produto(sf: MultiplicacaoSFOTS):
    """P2(s) ≡ (x*y + z = a*b), aritmética de n bits (módulo 2^n)."""
    return lambda s: s.x * s.y + s.z == s.a * s.b


def seguranca_simples(sf: MultiplicacaoSFOTS):
    """P(s) ≡ ¬E(s)  (o estado de erro nunca é acessível)."""
    return lambda s: Not(sf.erro(s))


def seguranca_reforcada(sf: MultiplicacaoSFOTS):
    """Q(s) ≡ ¬E(s) ∧ (x*y + z = a*b em 2n bits) ∧ (a,b < 2^(n/2)).
    Q ⇒ P e Q é indutivo: o reforço é o "look ahead" que a k-indução precisa."""
    n = sf.n
    limite = BitVecVal(2 ** (n // 2), n)
    return lambda s: And(
        Not(sf.erro(s)),
        sf.produto_largo(s) == sf.ab_largo(s),
        ULT(s.a, limite), ULT(s.b, limite),
    )


# 4. k-indução
def _valor(modelo, v):
    r = modelo.eval(v, model_completion=True)
    try:
        return r.as_long()
    except AttributeError:  # constante do EnumSort
        return str(r)


def extrai_traco(modelo, estados):
    """Converte os estados de um modelo Z3 em dicionários legíveis."""
    nomes = ("pc", "a", "b", "x", "y", "z")
    return [{nm: _valor(modelo, v) for nm, v in zip(nomes, e.todas())} for e in estados]


@dataclass
class ResultadoK:
    k: int
    base_ok: bool | None = None       # condição (a) para j = 0..k-1
    passo_ok: bool | None = None      # condição (b)
    falha: str | None = None          # "base j=<j>" ou "passo"
    contra_exemplo: list | None = None
    segundos: float = 0.0
    estados_z3: list = field(default_factory=list, repr=False)

    @property
    def provado(self) -> bool:
        return bool(self.base_ok) and bool(self.passo_ok)

    @property
    def veredicto(self) -> str:
        if self.provado:
            return "PROVADO"
        if self.base_ok is False:
            return "REFUTADO (base)"
        if self.base_ok is None or self.passo_ok is None:
            return "DESCONHECIDO (timeout)"
        return "NÃO INDUTIVO (passo)"


def k_inducao(sf: MultiplicacaoSFOTS, P, k: int, timeout_ms: int | None = None,
              tag: str = "k", dividir_ramos: bool = False) -> ResultadoK:
    """Verifica G P no SFOTS por k-indução (Cap. 3, 2ª parte):

      (a)  I(X0) ∧ ⋀_{i<j} T(Xi,Xi+1) ∧ ¬P(Xj)  é unsat, para j = 0..k-1
      (b)  ⋀_{i<k} (P(Xi) ∧ T(Xi,Xi+1)) ∧ ¬P(Xk)  é unsat

    Otimização (`dividir_ramos=True`): T é uma disjunção de 5 ramos exclusivos
    (stop, even, odd, sinks). Como  A ∧ (T1 ∨ … ∨ T5) ∧ ¬B  é unsat sse cada
    A ∧ Ti ∧ ¬B é unsat, a condição (b) é decomposta em 5^k problemas menores.
    É logicamente equivalente, mas muito mais rápida quando P contém
    multiplicações (o solver não tem de descobrir sozinho a análise por casos).
    """
    t0 = time.perf_counter()
    est = [sf.estado(f"{tag}{i}") for i in range(k + 1)]
    res = ResultadoK(k=k, estados_z3=est)

    def novo_solver():
        s = Solver()
        if timeout_ms:
            s.set("timeout", timeout_ms)
        return s

    # condição (a): um único solver, a cadeia cresce com j
    s = novo_solver()
    s.add(sf.init(est[0]))
    res.base_ok = True
    for j in range(k):
        s.push()
        s.add(Not(P(est[j])))
        r = s.check()
        if r == sat:
            res.base_ok, res.falha = False, f"base j={j}"
            res.contra_exemplo = extrai_traco(s.model(), est[: j + 1])
            s.pop()
            break
        if r == unknown:
            res.base_ok = None
            s.pop()
            break
        s.pop()
        s.add(sf.trans(est[j], est[j + 1]))

    # condição (b)
    if res.base_ok and not dividir_ramos:
        s2 = novo_solver()
        for i in range(k):
            s2.add(P(est[i]), sf.trans(est[i], est[i + 1]))
        s2.add(Not(P(est[k])))
        r = s2.check()
        if r == unsat:
            res.passo_ok = True
        elif r == sat:
            res.passo_ok, res.falha = False, "passo"
            res.contra_exemplo = extrai_traco(s2.model(), est)
        else:
            res.passo_ok = None
    elif res.base_ok:
        nomes = list(sf.ramos(est[0], est[1]).keys())
        res.passo_ok = True
        for escolha in itertools.product(nomes, repeat=k):
            s2 = novo_solver()
            for i, nome in enumerate(escolha):
                s2.add(P(est[i]), est[i + 1].a == est[i].a, est[i + 1].b == est[i].b,
                       sf.ramos(est[i], est[i + 1])[nome])
            s2.add(Not(P(est[k])))
            r = s2.check()
            if r == sat:
                res.passo_ok, res.falha = False, "passo"
                res.contra_exemplo = extrai_traco(s2.model(), est)
                break
            if r == unknown:
                res.passo_ok = None
                break
    res.segundos = time.perf_counter() - t0
    return res


# 5. BMC (contra-exemplos e limites de passos)
def bmc_alcanca(sf: MultiplicacaoSFOTS, alvo, K: int, timeout_ms: int | None = None,
                exato: bool = False):
    """Procura um traço I → ... com K transições que alcance `alvo`
    (em algum instante j ≤ K, ou exatamente em K se `exato`).
    Devolve (estado_z3, traço), traço=None se unsat; 'unknown' se timeout."""
    est = [sf.estado(f"bmc{i}") for i in range(K + 1)]
    s = Solver()
    if timeout_ms:
        s.set("timeout", timeout_ms)
    s.add(sf.init(est[0]))
    for i in range(K):
        s.add(sf.trans(est[i], est[i + 1]))
    s.add(alvo(est[K]) if exato else Or([alvo(e) for e in est]))
    r = s.check()
    if r == sat:
        return "sat", extrai_traco(s.model(), est)
    return ("unsat" if r == unsat else "unknown"), None


# 5b. PDR (extra): segurança sem reforçar a propriedade à mão
def pdr_erro_acessivel(sf: MultiplicacaoSFOTS, timeout_ms: int | None = 120_000) -> str:
    """Pergunta ao PDR do Z3 (motor Spacer) se o estado de erro é acessível.

    O sistema é escrito como cláusulas de Horn sobre um predicado Inv (estados
    acessíveis):   I(s) → Inv(s) ;   Inv(s) ∧ T(s,s') → Inv(s') ;   Inv(s) ∧ E(s) → ⊥.
    Devolve "unsat" (erro inacessível: o PDR encontrou um invariante indutivo
    que o exclui), "sat" (erro acessível) ou "unknown" (tempo esgotado).
    """
    fp = Fixedpoint()
    fp.set(engine="spacer")
    if timeout_ms:
        fp.set("timeout", timeout_ms)
    s, t = sf.estado("s"), sf.estado("t")
    fp.declare_var(*s.todas(), *t.todas())
    inv = Function("Inv", *[v.sort() for v in s.todas()], BoolSort())
    fp.register_relation(inv)
    fp.rule(inv(*s.todas()), sf.init(s))
    fp.rule(inv(*t.todas()), [inv(*s.todas()), sf.trans(s, t)])
    try:
        return str(fp.query(And(inv(*s.todas()), sf.erro(s))))
    except Z3Exception:       # tempo esgotado
        return "unknown"


def pdr_isolado(n: int, restringir_entradas: bool, timeout_s: int = 150) -> str:
    """Corre `pdr_erro_acessivel` num processo Python à parte.

    O Spacer usa muita pilha; dentro de um notebook (que corre as células numa
    thread) isso pode rebentar o processo todo. Assim, qualquer falha fica
    contida e é devolvida como texto ("unsat", "sat", "unknown" ou "falhou").
    """
    import subprocess
    import sys
    from pathlib import Path

    codigo = (
        "import sys; sys.path.insert(0, sys.argv[1]); import sfots_mult as M; "
        f"print(M.pdr_erro_acessivel(M.MultiplicacaoSFOTS({int(n)}, {bool(restringir_entradas)}), "
        f"timeout_ms={int(timeout_s) * 1000 - 5000}))"
    )
    try:
        p = subprocess.run([sys.executable, "-c", codigo, str(Path(__file__).resolve().parent)],
                           capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return "unknown"
    saida = p.stdout.strip().splitlines()
    return saida[-1] if p.returncode == 0 and saida else "falhou"


# 6. Propriedade de animação  F parado   (método do "look ahead" P*)
def p_estrela(sf: MultiplicacaoSFOTS):
    """P*(s, s') ≡ (¬parado(s) → R(s') < R(s)) ∧ (parado(s) → s' = s)."""
    def P(s, t):
        return And(
            Implies(Not(sf.parado(s)), ULT(sf.medida(t), sf.medida(s))),
            Implies(sf.parado(s), iguais(s, t)),
        )
    return P


def animacao(sf: MultiplicacaoSFOTS, timeout_ms: int | None = None) -> dict:
    """As 4 condições do Cap. 3 ("Look aheads") para Σ ⊨ F parado.
    Devolve {nome: "unsat"|"sat"|"unknown"}; tudo unsat ⇒ F parado."""
    X, Y, Z = sf.estado("X"), sf.estado("Y"), sf.estado("Z")
    Ps = p_estrela(sf)

    def chk(*formulas):
        s = Solver()
        if timeout_ms:
            s.set("timeout", timeout_ms)
        s.add(*formulas)
        r = s.check()
        return "unsat" if r == unsat else ("sat" if r == sat else "unknown")

    return {
        # 1. "parado" é indutivo: depois de parar continua parado
        "parado_indutivo": chk(sf.parado(X), sf.trans(X, Y), Not(sf.parado(Y))),
        # 2. a relação é total: todo o estado tem sucessor (os traços são infinitos)
        "T_total": chk(Not(Or(list(sf.guardas(X).values())))),
        # 3. P* é indutivo (precisa de 3 clones X, Y, Z)
        "Pestrela_indutivo": chk(Ps(X, Y), sf.trans(X, Y), sf.trans(Y, Z), Not(Ps(Y, Z))),
        # 4. P* vale no estado inicial e no seguinte
        "Pestrela_inicial": chk(sf.init(X), sf.trans(X, Y), Not(Ps(X, Y))),
    }


# 7. Oráculo em Python puro (usado nos testes)
def passo_ref(pc: str, a: int, b: int, x: int, y: int, z: int, n: int):
    """Um passo do programa, com aritmética de n bits. Devolve o estado seguinte."""
    mask = (1 << n) - 1
    if pc != "DO":
        return pc, a, b, x, y, z
    if y == 0:
        return "STOP", a, b, x, y, z
    if y % 2 == 0:
        ov = (x >> (n - 1)) & 1 == 1
        return ("ERROR" if ov else "DO"), a, b, (x << 1) & mask, y >> 1, z
    ov = z + x > mask
    return ("ERROR" if ov else "DO"), a, b, x, y - 1, (z + x) & mask


def referencia(a: int, b: int, n: int):
    """Executa o programa até parar. Devolve (pc_final, x, y, z, nº de transições
    até ao 1º estado parado)."""
    est = ("DO", a, b, a, b, 0)
    passos = 0
    while est[0] == "DO":
        est = passo_ref(*est, n)
        passos += 1
    return est[0], est[3], est[4], est[5], passos


def traco_ref(a: int, b: int, n: int):
    """Lista de estados (pc, x, y, z) por que o programa passa, do inicial até
    ao primeiro estado parado. Serve para ilustrar a execução passo a passo."""
    est = ("DO", a, b, a, b, 0)
    percurso = [(est[0], est[3], est[4], est[5])]
    while est[0] == "DO":
        est = passo_ref(*est, n)
        percurso.append((est[0], est[3], est[4], est[5]))
    return percurso
