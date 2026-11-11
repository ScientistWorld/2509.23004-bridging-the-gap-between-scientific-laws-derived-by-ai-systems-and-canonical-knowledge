"""Exact sparse multivariate polynomials over Q with a safe, restricted parser.

Pure Python (no SymPy): polynomials are dicts mapping exponent tuples to
``fractions.Fraction`` coefficients over a fixed, ordered variable list.
The parser accepts only integers, the given variable names, ``+ - * / ^ **``
and parentheses; division is allowed only by nonzero constants. Size limits
bound the work an adversarial string can cause.
"""

from __future__ import annotations

import re
from fractions import Fraction
from math import gcd

DEFAULT_LIMITS = {
    "max_chars": 4000,
    "max_terms": 400,
    "max_degree": 24,
    "max_exponent": 12,
    "max_int_digits": 60,
}

_TOKEN = re.compile(r"\s*(?:(\d+)|([A-Za-z_][A-Za-z0-9_]*)|(\*\*|[-+*/^()]))")


class PolyError(ValueError):
    """Raised for malformed, non-polynomial, or oversized expressions."""


def _lcm(a: int, b: int) -> int:
    return a // gcd(a, b) * b


class Poly:
    __slots__ = ("nvars", "terms")

    def __init__(self, nvars: int, terms: dict | None = None):
        self.nvars = nvars
        self.terms = {k: v for k, v in (terms or {}).items() if v != 0}

    # -- constructors -----------------------------------------------------
    @classmethod
    def const(cls, nvars: int, value) -> "Poly":
        return cls(nvars, {(0,) * nvars: Fraction(value)})

    @classmethod
    def var(cls, nvars: int, index: int) -> "Poly":
        exp = [0] * nvars
        exp[index] = 1
        return cls(nvars, {tuple(exp): Fraction(1)})

    # -- queries ------------------------------------------------------------
    def is_zero(self) -> bool:
        return not self.terms

    def is_constant(self) -> bool:
        return all(sum(e) == 0 for e in self.terms)

    def constant_value(self) -> Fraction:
        return self.terms.get((0,) * self.nvars, Fraction(0))

    def total_degree(self) -> int:
        return max((sum(e) for e in self.terms), default=0)

    def used_variables(self) -> set[int]:
        used = set()
        for exp in self.terms:
            for i, e in enumerate(exp):
                if e:
                    used.add(i)
        return used

    def num_terms(self) -> int:
        return len(self.terms)

    # -- arithmetic -----------------------------------------------------------
    def __add__(self, other: "Poly") -> "Poly":
        out = dict(self.terms)
        for k, v in other.terms.items():
            out[k] = out.get(k, Fraction(0)) + v
        return Poly(self.nvars, out)

    def __neg__(self) -> "Poly":
        return Poly(self.nvars, {k: -v for k, v in self.terms.items()})

    def __sub__(self, other: "Poly") -> "Poly":
        return self + (-other)

    def scale(self, c) -> "Poly":
        c = Fraction(c)
        return Poly(self.nvars, {k: v * c for k, v in self.terms.items()})

    def mul(self, other: "Poly", max_terms: int | None = None) -> "Poly":
        out: dict = {}
        for k1, v1 in self.terms.items():
            for k2, v2 in other.terms.items():
                k = tuple(a + b for a, b in zip(k1, k2))
                out[k] = out.get(k, Fraction(0)) + v1 * v2
            if max_terms is not None and len(out) > 4 * max_terms:
                raise PolyError("expression expands to too many terms")
        return Poly(self.nvars, out)

    def substitute_scaled(self, scales: list) -> "Poly":
        """Return p(s_1*x_1, ..., s_n*x_n) for rational scale factors."""
        out = {}
        for exp, c in self.terms.items():
            f = Fraction(c)
            for s, e in zip(scales, exp):
                if e:
                    f *= Fraction(s) ** e
            out[exp] = f
        return Poly(self.nvars, out)

    # -- normal forms -------------------------------------------------------
    def integer_primitive(self) -> dict:
        """Integer-coefficient primitive associate with positive leading term."""
        if not self.terms:
            return {}
        den = 1
        for v in self.terms.values():
            den = _lcm(den, v.denominator)
        ints = {k: int(v * den) for k, v in self.terms.items()}
        g = 0
        for v in ints.values():
            g = gcd(g, abs(v))
        lead = max(ints, key=lambda e: (sum(e), e))
        sign = -1 if ints[lead] < 0 else 1
        return {k: sign * v // g for k, v in ints.items()}

    def to_string(self, names: list[str], primitive: bool = True) -> str:
        """Deterministic Singular/SymPy-compatible string (integer coefficients)."""
        if not self.terms:
            return "0"
        coeffs = self.integer_primitive() if primitive else None
        if coeffs is None:
            raise PolyError("non-primitive printing of rationals is not supported")
        parts = []
        for exp in sorted(coeffs, key=lambda e: (-sum(e), tuple(-x for x in e))):
            c = coeffs[exp]
            mon = "*".join(
                (names[i] if e == 1 else f"{names[i]}^{e}") for i, e in enumerate(exp) if e
            )
            mag = abs(c)
            if mon:
                body = mon if mag == 1 else f"{mag}*{mon}"
            else:
                body = str(mag)
            if not parts:
                parts.append(("-" if c < 0 else "") + body)
            else:
                parts.append((" - " if c < 0 else " + ") + body)
        return "".join(parts)


def tokenize(text: str, max_int_digits: int) -> list[tuple[str, object]]:
    text = text.strip()
    pos = 0
    out: list[tuple[str, object]] = []
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m or m.end() == pos:
            raise PolyError(f"invalid character near position {pos}")
        num, name, op = m.groups()
        if num is not None:
            if len(num) > max_int_digits:
                raise PolyError("integer literal too long")
            out.append(("num", int(num)))
        elif name is not None:
            out.append(("var", name))
        else:
            out.append(("op", "^" if op == "**" else op))
        pos = m.end()
    return out


class _Parser:
    def __init__(self, tokens, var_index: dict[str, int], nvars: int, limits: dict):
        self.toks = tokens
        self.i = 0
        self.var_index = var_index
        self.n = nvars
        self.lim = limits

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else (None, None)

    def take(self):
        tok = self.peek()
        self.i += 1
        return tok

    def check(self, p: Poly) -> Poly:
        if p.num_terms() > self.lim["max_terms"]:
            raise PolyError("too many terms")
        if p.total_degree() > self.lim["max_degree"]:
            raise PolyError("degree too large")
        return p

    def parse(self) -> Poly:
        if not self.toks:
            raise PolyError("empty expression")
        p = self.expr()
        if self.i != len(self.toks):
            raise PolyError("unexpected trailing tokens")
        return p

    def expr(self) -> Poly:
        p = self.term()
        while self.peek() in (("op", "+"), ("op", "-")):
            _, op = self.take()
            q = self.term()
            p = self.check(p + q if op == "+" else p - q)
        return p

    def term(self) -> Poly:
        p = self.unary()
        while self.peek() in (("op", "*"), ("op", "/")):
            _, op = self.take()
            q = self.unary()
            if op == "*":
                p = self.check(p.mul(q, self.lim["max_terms"]))
            else:
                if not q.is_constant() or q.is_zero():
                    raise PolyError("division is only allowed by nonzero constants")
                p = p.scale(1 / q.constant_value())
        return p

    def unary(self) -> Poly:
        kind, val = self.peek()
        if kind == "op" and val == "+":
            self.take()
            return self.unary()
        if kind == "op" and val == "-":
            self.take()
            return -self.unary()
        return self.power()

    def power(self) -> Poly:
        base = self.atom()
        if self.peek() == ("op", "^"):
            self.take()
            kind, val = self.take()
            if kind != "num":
                raise PolyError("exponent must be a nonnegative integer literal")
            if val > self.lim["max_exponent"]:
                raise PolyError("exponent too large")
            out = Poly.const(self.n, 1)
            for _ in range(val):
                out = self.check(out.mul(base, self.lim["max_terms"]))
            if self.peek() == ("op", "^"):
                raise PolyError("chained exponents are not allowed")
            return out
        return base

    def atom(self) -> Poly:
        kind, val = self.take()
        if kind == "num":
            return Poly.const(self.n, val)
        if kind == "var":
            if val not in self.var_index:
                raise PolyError(f"unknown variable {val!r}")
            return Poly.var(self.n, self.var_index[val])
        if kind == "op" and val == "(":
            p = self.expr()
            if self.take() != ("op", ")"):
                raise PolyError("missing closing parenthesis")
            return p
        raise PolyError("unexpected token")


def parse_poly(text, names: list[str], limits: dict | None = None) -> Poly:
    """Parse ``text`` into a Poly over ``names``; raise PolyError when invalid."""
    lim = dict(DEFAULT_LIMITS)
    if limits:
        lim.update(limits)
    if not isinstance(text, str):
        raise PolyError("polynomial must be a string")
    if len(text) > lim["max_chars"]:
        raise PolyError("polynomial string too long")
    tokens = tokenize(text, lim["max_int_digits"])
    index = {name: i for i, name in enumerate(names)}
    return _Parser(tokens, index, len(names), lim).parse()


def canonical(text, names: list[str], limits: dict | None = None) -> str:
    """Canonical primitive integer string of a polynomial, or raise PolyError."""
    p = parse_poly(text, names, limits)
    if p.is_zero():
        raise PolyError("zero polynomial")
    return p.to_string(names)
