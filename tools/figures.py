"""SVG diagram generator for the study guide.

Every figure is computed from the same equations used in the worked examples,
so the pictures and the algebra always agree. Styling is done with CSS classes
(defined in src/assets/style.css) so figures follow the light/dark theme and print well.
"""
import math
from html import escape


class Plot:
    def __init__(self, xmax, ymax, xlabel="Quantity, Q", ylabel="Price, P",
                 w=560, h=400, ml=62, mr=34, mt=22, mb=52, xmin=0, ymin=0,
                 title=""):
        self.xmin, self.xmax, self.ymin, self.ymax = xmin, xmax, ymin, ymax
        self.w, self.h, self.ml, self.mr, self.mt, self.mb = w, h, ml, mr, mt, mb
        self.xlabel, self.ylabel, self.title = xlabel, ylabel, title
        self.layers = {"shade": [], "guide": [], "curve": [], "point": [], "text": []}
        self.xticks, self.yticks = [], []
        self.unders = []

    # coordinate transforms -------------------------------------------------
    def px(self, x):
        return self.ml + (x - self.xmin) / (self.xmax - self.xmin) * (self.w - self.ml - self.mr)

    def py(self, y):
        return self.h - self.mb - (y - self.ymin) / (self.ymax - self.ymin) * (self.h - self.mt - self.mb)

    def P(self, x, y):
        return f"{self.px(x):.1f},{self.py(y):.1f}"

    # primitives ---------------------------------------------------------------
    def curve(self, pts, cls="c1", label=None, at=None, dx=6, dy=-6, anchor="start"):
        d = "M" + " L".join(self.P(x, y) for x, y in pts
                            if self.ymin - 1e-9 <= y <= self.ymax * 1.02 + 1e-9 and self.xmin - 1e-9 <= x <= self.xmax + 1e-9)
        self.layers["curve"].append(f'<path class="{cls}" d="{d}"/>')
        if label:
            if at is None:
                inside = [(x, y) for x, y in pts if self.ymin <= y <= self.ymax and self.xmin <= x <= self.xmax]
                at = inside[-1]
            self.text(at[0], at[1], label, cls=f"lbl {cls.split()[0]}-t", dx=dx, dy=dy, anchor=anchor)
        return self

    def fn(self, f, x0=None, x1=None, n=160, **kw):
        x0 = self.xmin if x0 is None else x0
        x1 = self.xmax if x1 is None else x1
        pts = []
        for i in range(n + 1):
            x = x0 + (x1 - x0) * i / n
            try:
                y = f(x)
            except (ZeroDivisionError, ValueError):
                continue
            pts.append((x, y))
        return self.curve(pts, **kw)

    def line(self, p, q, cls="c1", label=None, at="end", **kw):
        self.layers["curve"].append(
            f'<line class="{cls}" x1="{self.px(p[0]):.1f}" y1="{self.py(p[1]):.1f}" x2="{self.px(q[0]):.1f}" y2="{self.py(q[1]):.1f}"/>')
        if label:
            pt = q if at == "end" else (p if at == "start" else at)
            self.text(pt[0], pt[1], label, cls=f"lbl {cls.split()[0]}-t", **kw)
        return self

    def vline(self, x, y0=None, y1=None, cls="guide"):
        return self.line((x, self.ymin if y0 is None else y0), (x, self.ymax if y1 is None else y1), cls=cls)

    def hline(self, y, x0=None, x1=None, cls="guide"):
        return self.line((self.xmin if x0 is None else x0, y), (self.xmax if x1 is None else x1, y), cls=cls)

    def drop(self, x, y, xl=None, yl=None):
        """Dashed guides from a point down to the x-axis and across to the y-axis."""
        self.layers["guide"].append(
            f'<polyline class="guide" points="{self.P(self.xmin, y)} {self.P(x, y)} {self.P(x, self.ymin)}"/>')
        if xl is not None:
            self.xticks.append((x, xl))
        if yl is not None:
            self.yticks.append((y, yl))
        return self

    def poly(self, pts, cls="sh-cs", label=None, at=None, lcls="lbl small"):
        self.layers["shade"].append(f'<polygon class="{cls}" points="{" ".join(self.P(x, y) for x, y in pts)}"/>')
        if label:
            if at is None:
                at = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
            self.text(at[0], at[1], label, cls=lcls, anchor="middle", dy=4)
        return self

    def region(self, f_top, f_bot, x0, x1, cls="sh-cs", label=None, at=None, n=60):
        top = [(x0 + (x1 - x0) * i / n, f_top(x0 + (x1 - x0) * i / n)) for i in range(n + 1)]
        bot = [(x0 + (x1 - x0) * i / n, f_bot(x0 + (x1 - x0) * i / n)) for i in range(n + 1)][::-1]
        return self.poly(top + bot, cls=cls, label=label, at=at)

    def dot(self, x, y, label=None, dx=7, dy=-7, anchor="start", cls="pt"):
        self.layers["point"].append(f'<circle class="{cls}" cx="{self.px(x):.1f}" cy="{self.py(y):.1f}" r="4"/>')
        if label:
            self.text(x, y, label, cls="lbl strong", dx=dx, dy=dy, anchor=anchor)
        return self

    def text(self, x, y, s, cls="lbl", dx=0, dy=0, anchor="start"):
        self.layers["text"].append(
            f'<text class="{cls}" x="{self.px(x) + dx:.1f}" y="{self.py(y) + dy:.1f}" text-anchor="{anchor}">{escape(s)}</text>')
        return self

    def arrow(self, p, q, cls="arr"):
        self.layers["curve"].append(
            f'<line class="{cls}" marker-end="url(#ah)" x1="{self.px(p[0]):.1f}" y1="{self.py(p[1]):.1f}" x2="{self.px(q[0]):.1f}" y2="{self.py(q[1]):.1f}"/>')
        return self

    def under(self, x0, x1, label, row=0):
        """Double-headed bracket arrow drawn below the x-axis (e.g. SE / IE)."""
        self.unders.append((x0, x1, label, row))
        return self

    def xtick(self, x, s):
        self.xticks.append((x, s)); return self

    def ytick(self, y, s):
        self.yticks.append((y, s)); return self

    # output -------------------------------------------------------------------
    def svg(self, aria):
        x0, y0 = self.px(self.xmin), self.py(self.ymin)
        x1, y1 = self.px(self.xmax), self.py(self.ymax)
        out = [f'<svg class="fig" viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{escape(aria)}" xmlns="http://www.w3.org/2000/svg">',
               '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
               '<path class="ahead" d="M0,0 L10,5 L0,10 z"/></marker></defs>']
        for k in ("shade", "guide", "curve"):
            out += self.layers[k]
        out.append(f'<line class="ax" x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1 + 8:.1f}" y2="{y0:.1f}"/>')
        out.append(f'<line class="ax" x1="{x0:.1f}" y1="{y0:.1f}" x2="{x0:.1f}" y2="{y1 - 8:.1f}"/>')
        for x, s in self.xticks:
            out.append(f'<text class="tick" x="{self.px(x):.1f}" y="{y0 + 17:.1f}" text-anchor="middle">{escape(s)}</text>')
        for y, s in self.yticks:
            out.append(f'<text class="tick" x="{x0 - 7:.1f}" y="{self.py(y) + 4:.1f}" text-anchor="end">{escape(s)}</text>')
        for ux0, ux1, ul, row in self.unders:
            yy = y0 + 34 + 20 * row
            sgn = 1 if ux1 >= ux0 else -1
            out.append(f'<line class="arr" marker-end="url(#ah)" x1="{self.px(ux0) + 2 * sgn:.1f}" y1="{yy:.1f}" x2="{self.px(ux1) - 2 * sgn:.1f}" y2="{yy:.1f}"/>')
            out.append(f'<text class="lbl small strong" x="{(self.px(ux0) + self.px(ux1)) / 2:.1f}" y="{yy - 4:.1f}" text-anchor="middle">{escape(ul)}</text>')
        xly = self.h - 8 if self.unders else y0 + 38
        out.append(f'<text class="axl" x="{x1:.1f}" y="{xly:.1f}" text-anchor="end">{escape(self.xlabel)}</text>')
        out.append(f'<text class="axl" x="{x0 - 10:.1f}" y="{y1 - 10:.1f}" text-anchor="start">{escape(self.ylabel)}</text>')
        out += self.layers["point"] + self.layers["text"]
        out.append("</svg>")
        return "\n".join(out)


def pair(*svgs):
    return '<div class="fig-pair">' + "".join(svgs) + "</div>"


def flow(rows):
    """Simple box-and-arrow flow diagram rendered in HTML/CSS."""
    html = ['<div class="flow">']
    for i, r in enumerate(rows):
        if i:
            html.append('<div class="flow-arrow">&darr;</div>')
        html.append('<div class="flow-row">' + "".join(f'<div class="flow-box">{b}</div>' for b in r) + "</div>")
    html.append("</div>")
    return "".join(html)


F = {}


def fig(name):
    def deco(fn):
        F[name] = fn
        return fn
    return deco


# =============================================================================
# LECTURE 5 - INFLATION, PHILLIPS CURVE, MONETARY POLICY
# =============================================================================

@fig("pc_basic")
def _():
    p = Plot(12, 10, "Unemployment rate, u (%)", "Inflation, π (%)", ymin=-2)
    f = lambda u: -2 + 18 / u
    p.fn(f, 1.75, 12, cls="c1", label="Phillips curve", at=(4.6, f(4.6)), dx=8, dy=-8)
    p.hline(0, cls="ax-soft")
    p.dot(3, f(3), "A: low u, high π")
    p.dot(7.5, f(7.5), "B: high u, low π")
    for u in (2, 4, 6, 8, 10):
        p.xtick(u, str(u))
    for y in (0, 4, 8):
        p.ytick(y, str(y))
    p.ytick(-2, "−2")
    return p.svg("Downward-sloping, convex Phillips curve: inflation falls as unemployment rises.")


@fig("pc_eapc")
def _():
    p = Plot(13, 10, "Unemployment rate, u (%)", "Inflation, π (%)")
    us = 5
    for pe, cls in ((2, "c1"), (5, "c3"), (8, "c4")):
        g = lambda u, pe=pe: pe - (u - us)
        u_end = min(10, pe + us - 0.5)
        p.fn(g, 1, u_end, cls=cls, label=f"SRPC (πᵉ = {pe}%)", at=(u_end, g(u_end)), dx=6, dy=4)
    p.vline(us, 0, 9.8, cls="c2")
    p.text(us, 9.6, "LRPC (vertical at u*)", cls="lbl c2-t", dx=6)
    p.dot(us, 2, "A", dx=8, dy=14)
    p.dot(2, 5, "B", dx=-16)
    p.dot(us, 5, "C", dx=8, dy=14)
    p.dot(2, 8, "D", dx=-16)
    p.dot(us, 8, "E", dx=8, dy=14)
    p.arrow((us - 0.15, 2.3), (2.25, 4.75))
    p.arrow((2.2, 5.0), (us - 0.25, 5.0))
    p.arrow((us - 0.15, 5.3), (2.25, 7.75))
    p.arrow((2.2, 8.0), (us - 0.25, 8.0))
    p.xtick(2, "u₁").xtick(us, "u*")
    p.ytick(2, "2").ytick(5, "5").ytick(8, "8")
    return p.svg("Expectations-augmented Phillips curves shift up as expected inflation rises; the long-run Phillips curve is vertical at the natural rate.")


@fig("ws_ps")
def _():
    p = Plot(104, 10, "Employment rate (%)", "Real wage, w/P", xmin=40)
    ps = 6.0
    ws = lambda n: 2 + 6 * ((n - 40) / 55) ** 2
    p.hline(ps, 40, 104, cls="c2")
    p.text(41, ps, "Price-setting curve (PS)", cls="lbl c2-t", dy=-8)
    p.fn(ws, 40, 97, cls="c1", label="Wage-setting curve (WS)", at=(72, ws(72)), dx=-6, dy=-10, anchor="end")
    n_star = 40 + 55 * math.sqrt((ps - 2) / 6)
    p.dot(n_star, ps, "X", dx=-6, dy=-10, anchor="end")
    n_hi = 94
    p.dot(n_hi, ws(n_hi), "B", dx=-14, dy=0)
    p.dot(n_hi, ps)
    p.line((n_hi, ps), (n_hi, ws(n_hi)), cls="gap")
    p.text(n_hi, (ps + ws(n_hi)) / 2, "bargaining", cls="lbl small strong", dx=8)
    p.text(n_hi, (ps + ws(n_hi)) / 2 - 0.45, "gap", cls="lbl small strong", dx=8)
    p.drop(n_star, ps, xl="N* (u = u*)")
    p.layers["guide"].append(f'<line class="guide" x1="{p.px(n_hi):.1f}" y1="{p.py(0):.1f}" x2="{p.px(n_hi):.1f}" y2="{p.py(ps):.1f}"/>')
    p.xtick(n_hi, "N₁")
    p.text(60, 1.0, "u > u*: gap < 0, inflation falls", cls="lbl small", anchor="middle")
    return p.svg("Wage-setting curve rises with employment; price-setting curve is flat. At employment above the equilibrium the WS lies above PS creating a bargaining gap.")


@fig("multiplier")
def _():
    p = Plot(100, 100, "Output (income), Y", "Aggregate demand, AD", mr=120)
    k = 0.5
    p.line((0, 0), (96, 96), cls="ax-soft")
    p.text(96, 96, "Y = AD (45°)", cls="lbl small", dx=6, dy=4)
    for a0, cls, lab, dy in ((40, "c1", "AD₀", -4), (36, "c3 dashed", "AD₂: c₀′, lower r′", 6), (30, "c2", "AD₁: lower c₀′", 14)):
        p.fn(lambda y, a0=a0: a0 + k * y, 0, 92, cls=cls, label=lab, at=(92, a0 + k * 92), dx=6, dy=dy)
    p.dot(80, 80, "A", dx=-16, dy=-4)
    p.dot(60, 60, "B", dx=8, dy=16)
    p.dot(72, 72, "C", dx=8, dy=16)
    p.drop(80, 80, xl="Y₀")
    p.drop(60, 60, xl="Y₁")
    p.drop(72, 72, xl="Y₂")
    return p.svg("Keynesian cross: a fall in autonomous consumption shifts AD down from A to B; a cut in the policy rate raises investment and shifts AD back up toward C.")


# =============================================================================
# LECTURE 6 - SUPPLY, DEMAND, ELASTICITY, CONSUMER CHOICE
# =============================================================================

D = lambda q: 10 - q        # course example: willingness to pay starts at 10
S = lambda q: 2 + q         # cost starts at 2


@fig("sd_eq")
def _():
    p = Plot(10, 12)
    p.fn(D, 0, 10, cls="c1", label="Demand", at=(8.6, D(8.6)), dy=-8)
    p.fn(S, 0, 10, cls="c2", label="Supply", at=(9, S(9)), dx=-6, dy=-8, anchor="end")
    p.dot(4, 6, "E", dx=8, dy=-4)
    p.drop(4, 6, xl="Q* = 4", yl="P* = 6")
    # surplus at P=8
    p.line((2, 8), (6, 8), cls="gap")
    p.text(4, 8, "surplus (Qs > Qd) at P = 8", cls="lbl small", dy=-8, anchor="middle")
    p.line((2, 4), (6, 4), cls="gap")
    p.text(4, 4, "shortage (Qd > Qs) at P = 4", cls="lbl small", dy=18, anchor="middle")
    p.ytick(8, "8").ytick(4, "4")
    return p.svg("Linear demand P = 10 − Q and supply P = 2 + Q intersect at Q* = 4, P* = 6. Above P*, surplus; below, shortage.")


@fig("sd_shift_d")
def _():
    p = Plot(10, 12, title="Increase in demand")
    p.fn(D, 0, 10, cls="c1", label="D₀", at=(9, D(9)), dy=-6)
    p.fn(lambda q: 12 - q, 2, 10, cls="c1 dashed", label="D₁", at=(9.5, 12 - 9.5), dy=-6)
    p.fn(S, 0, 10, cls="c2", label="S", at=(9, S(9)), dx=-6, dy=-6, anchor="end")
    p.dot(4, 6, "E₀", dx=-22, dy=-4)
    p.dot(5, 7, "E₁", dx=6, dy=-8)
    p.drop(4, 6, xl="4", yl="6")
    p.drop(5, 7, xl="5", yl="7")
    p.arrow((6.5, 3.8), (7.6, 4.6))
    return p.svg("A rightward shift of demand raises both equilibrium price and quantity.")


@fig("sd_shift_s")
def _():
    p = Plot(10, 12, title="Decrease in supply")
    p.fn(D, 0, 10, cls="c1", label="D", at=(9, D(9)), dy=-6)
    p.fn(S, 0, 10, cls="c2", label="S₀", at=(9.4, S(9.4)), dx=-6, dy=10, anchor="end")
    p.fn(lambda q: 4 + q, 0, 8, cls="c2 dashed", label="S₁", at=(7.6, 11.6), dx=-6, dy=0, anchor="end")
    p.dot(4, 6, "E₀", dx=8, dy=12)
    p.dot(3, 7, "E₁", dx=-24, dy=-6)
    p.drop(4, 6, xl="4", yl="6")
    p.drop(3, 7, xl="3", yl="7")
    p.arrow((6.6, 8.6), (5.7, 9.5))
    return p.svg("A leftward shift of supply raises price and lowers quantity.")


@fig("elasticity_linear")
def _():
    a, b = 10, 1  # P = 10 - Q
    p1 = Plot(10, 11, "Quantity, Q", "Price, P", h=340, w=420, mr=20)
    p1.fn(lambda q: a - b * q, 0, 10, cls="c1", label="P = 10 − Q", at=(7.2, 2.8), dy=-8)
    p1.dot(5, 5, "|e| = 1", dx=8, dy=-6)
    p1.text(1.4, 8.0, "elastic |e| > 1", cls="lbl small")
    p1.text(6.4, 1.2, "inelastic |e| < 1", cls="lbl small")
    p1.drop(5, 5, xl="5", yl="5")
    p1.ytick(10, "10").xtick(10, "10")
    p2 = Plot(10, 30, "Quantity, Q", "Total revenue, TR = PQ", h=340, w=420, mr=20)
    p2.fn(lambda q: (a - b * q) * q, 0, 10, cls="c3", label="TR", at=(8.5, (a - 8.5) * 8.5), dy=-6)
    p2.dot(5, 25, "max TR (MR = 0)", dx=6, dy=-8)
    p2.drop(5, 25, xl="5", yl="25")
    p2.xtick(10, "10")
    return pair(p1.svg("Linear demand: elasticity is greater than one above the midpoint and less than one below."),
                p2.svg("Total revenue is maximised at the midpoint where demand is unit elastic."))


@fig("budget_ic")
def _():
    p = Plot(24, 85, "Good x", "Good y")
    p.line((0, 80), (20, 0), cls="c2")
    p.text(20, 0, "BL: 4x + y = 80", cls="lbl c2-t", dx=4, dy=-8)
    for U, cls, lab in ((250, "c1 thin", "U = 250"), (400, "c1", "U₀ = 400"), (650, "c1 thin", "U = 650")):
        p.fn(lambda x, U=U: U / x, U / 84, 24, cls=cls, label=lab, at=(24, U / 24), dx=-2, dy=-6, anchor="end")
    p.dot(10, 40, "E: MRS = Px/Py", dx=8, dy=-8)
    p.drop(10, 40, xl="x* = 10", yl="y* = 40")
    p.dot(4, 64, "F", dx=8)
    p.ytick(80, "80").xtick(20, "20")
    return p.svg("Budget line 4x + y = 80 is tangent to the indifference curve U = 400 at x = 10, y = 40.")


@fig("price_effect")
def _():
    p = Plot(85, 85, "Good x", "Good y", mb=86)
    p.line((0, 80), (20, 0), cls="c2")
    p.line((0, 80), (80, 0), cls="c2")
    p.line((0, 40), (40, 0), cls="c3 dashed")
    p.text(19, 6, "BL₀", cls="lbl c2-t", dx=6)
    p.text(74, 6, "BL₁", cls="lbl c2-t", dx=6)
    p.text(36, 4, "BLc", cls="lbl c3-t", dx=6)
    p.fn(lambda x: 400 / x, 400 / 84, 85, cls="c1", label="U₀ = 400", at=(52, 400 / 52), dx=0, dy=-8, anchor="middle")
    p.fn(lambda x: 1600 / x, 1600 / 84, 85, cls="c1", label="U₁ = 1600", at=(80, 20), dx=-4, dy=-6, anchor="end")
    p.dot(10, 40, "A", dx=-16, dy=-6)
    p.dot(20, 20, "C", dx=-16, dy=12)
    p.dot(40, 40, "B", dx=8, dy=-8)
    p.xtick(10, "10").xtick(20, "20").xtick(40, "40")
    for x, y in ((10, 40), (20, 20), (40, 40)):
        p.layers["guide"].append(f'<line class="guide" x1="{p.px(x):.1f}" y1="{p.py(0):.1f}" x2="{p.px(x):.1f}" y2="{p.py(y):.1f}"/>')
    p.under(10, 20, "SE", 0).under(20, 40, "IE", 0).under(10, 40, "total price effect", 1)
    return p.svg("Price of x falls from 4 to 1. Substitution effect A to C along U0; income effect C to B.")


@fig("giffen")
def _():
    p = Plot(30, 30, "Good x (Giffen)", "Good y", mb=86)
    p.line((0, 24), (12, 0), cls="c2")
    p.line((0, 24), (24, 0), cls="c2")
    p.line((0, 17), (17, 0), cls="c3 dashed")
    p.text(11, 2, "BL₀", cls="lbl c2-t", dx=6)
    p.text(22, 2, "BL₁", cls="lbl c2-t", dx=6)
    p.text(15, 2, "BLc", cls="lbl c3-t", dx=6)
    A, C, B = (8, 8), (11, 6), (6.5, 17.5)
    p.dot(*A, "A", dx=-16, dy=-2)
    p.dot(*C, "C", dx=8, dy=-2)
    p.dot(*B, "B", dx=8, dy=-6)
    p.arrow((A[0] + 0.3, A[1] - 0.2), (C[0] - 0.4, C[1] + 0.25))
    p.arrow((C[0] - 0.4, C[1] + 0.6), (B[0] + 0.4, B[1] - 0.8))
    p.text(15, 26, "SE: A → C (x rises)", cls="lbl small")
    p.text(15, 23.5, "IE: C → B (x falls by more)", cls="lbl small")
    p.text(15, 21, "Total: A → B (x falls as Px falls)", cls="lbl small strong")
    for pt in (A, C, B):
        p.layers["guide"].append(f'<line class="guide" x1="{p.px(pt[0]):.1f}" y1="{p.py(0):.1f}" x2="{p.px(pt[0]):.1f}" y2="{p.py(pt[1]):.1f}"/>')
    p.under(8, 11, "SE", 0).under(11, 6.5, "IE", 1)
    return p.svg("Giffen good: the negative income effect outweighs the substitution effect so quantity falls when price falls.")


@fig("demand_derivation")
def _():
    # U = xy, M = 80, py = 1: x = 40/px
    p1 = Plot(45, 85, "Good x", "Good y", h=340, w=420, mr=20)
    for px, cls in ((4, "c2"), (2, "c2"), (1, "c2")):
        p1.line((0, 80), (80 / px, 0), cls=cls)
        x = 40 / px
        p1.fn(lambda q, U=x * 40: U / q, x * 40 / 84, 45, cls="c1 thin")
        p1.dot(x, 40)
    p1.hline(40, 0, 45, cls="guide")
    p1.text(42, 40, "PCC", cls="lbl small strong", dy=-8, anchor="end")
    p1.xtick(10, "10").xtick(20, "20").xtick(40, "40")
    p2 = Plot(45, 5, "Good x", "Price of x, Px", h=340, w=420, mr=20)
    p2.fn(lambda x: 40 / x, 8.5, 45, cls="c1", label="x = 40/Pₓ", at=(28, 40 / 28), dy=-10)
    for px in (4, 2, 1):
        p2.dot(40 / px, px)
        p2.drop(40 / px, px, xl=str(int(40 / px)), yl=str(px))
    return pair(p1.svg("Price-consumption curve traced out as Px falls."),
                p2.svg("The resulting individual demand curve x = 40/Px."))


@fig("labour_leisure")
def _():
    N = 24
    p = Plot(26, 260, "Leisure, l (hours/day)", "Consumption, C (₹ per day)")
    for w, lab in ((5, "w = 5"), (10, "w = 10")):
        p.line((0, w * N), (N, 0), cls="c2", label=f"C = {w}(24 − l)", at=(0.3, w * N), dx=6, dy=-6)
    # U = l^0.5 C^0.5 -> l* = 12 for every w
    for w in (5, 10):
        U = math.sqrt(12 * w * 12)
        p.fn(lambda l, U=U: U * U / l, U * U / 255, 26, cls="c1 thin")
        p.dot(12, w * 12, f"l* = 12, C = {w * 12}", dx=8, dy=-6)
    p.vline(N, 0, 250, cls="guide")
    p.xtick(12, "12").xtick(N, "N = 24")
    return p.svg("Labour-leisure choice: budget line C = w(N − l); with Cobb-Douglas utility leisure stays at 12 hours as w changes.")


@fig("backward_bending")
def _():
    p = Plot(14, 60, "Hours of work, h = N − l", "Wage, w")
    pts = []
    for i in range(0, 201):
        w = 2 + 56 * i / 200
        h = 12.5 * (1 - math.exp(-(w - 2) / 7)) - 0.11 * max(0, w - 18) ** 1.25
        pts.append((h, w))
    p.curve(pts, cls="c1", label="Labour supply", at=pts[-1], dx=8, dy=4)
    hm, wm = max(pts)
    p.hline(wm, 0, hm, cls="guide")
    p.ytick(wm, "w̄")
    p.text(7, 6, "SE dominates: h ↑ as w ↑", cls="lbl small")
    p.text(6.5, 48, "IE dominates: h ↓ as w ↑", cls="lbl small")
    return p.svg("Backward-bending labour supply: hours rise with the wage until the income effect dominates.")


# =============================================================================
# LECTURE 7 - PRODUCTION, COSTS, PERFECT COMPETITION
# =============================================================================

TP = lambda L: 6 * L ** 2 - 0.4 * L ** 3      # total product
MPL = lambda L: 12 * L - 1.2 * L ** 2
APL = lambda L: 6 * L - 0.4 * L ** 2


@fig("tp_mp_ap")
def _():
    p1 = Plot(15, 280, "Labour, L", "Total product, Q", h=320, w=420, mr=20)
    p1.fn(TP, 0, 15, cls="c1", label="TP", at=(14.2, TP(14.2)), dx=-4, dy=-10, anchor="end")
    p1.dot(5, TP(5), "inflection (max MP)", dx=8, dy=10)
    p1.dot(7.5, TP(7.5), "ray tangent (max AP)", dx=8, dy=10)
    p1.dot(10, TP(10), "max TP (MP = 0)", dx=-4, dy=-10, anchor="end")
    p1.line((0, 0), (9.5, TP(7.5) / 7.5 * 9.5), cls="guide")
    p2 = Plot(15, 34, "Labour, L", "MP, AP", h=320, w=420, mr=20, ymin=-10)
    p2.fn(MPL, 0, 12.2, cls="c2", label="MPₗ", at=(11.4, MPL(11.4)), dx=-8, anchor="end")
    p2.fn(APL, 0, 15, cls="c3", label="APₗ", at=(14, APL(14)), dx=-6, dy=-8, anchor="end")
    p2.hline(0, cls="ax-soft")
    p2.dot(5, MPL(5), "", )
    p2.dot(7.5, APL(7.5), "MP = AP", dx=8, dy=-6)
    p2.dot(10, 0, "", )
    p2.xtick(5, "5").xtick(7.5, "7.5").xtick(10, "10")
    return pair(p1.svg("Total product curve with increasing then diminishing marginal returns."),
                p2.svg("Marginal product cuts average product at the maximum of average product."))


def cubic_costs():
    F_ = 60
    VC = lambda q: 12 * q - 2 * q ** 2 + 0.2 * q ** 3
    MC = lambda q: 12 - 4 * q + 0.6 * q ** 2
    AVC = lambda q: 12 - 2 * q + 0.2 * q ** 2
    ATC = lambda q: F_ / q + AVC(q)
    return F_, VC, MC, AVC, ATC


@fig("cost_curves")
def _():
    F_, VC, MC, AVC, ATC = cubic_costs()
    p = Plot(12, 30, "Output, Q", "Cost per unit (₹)")
    p.fn(MC, 0.3, 11.5, cls="c2", label="MC", at=(10.6, MC(10.6)), dx=-8, anchor="end")
    p.fn(ATC, 2.2, 12, cls="c1", label="ATC", at=(12, ATC(12)), dx=-4, dy=-8, anchor="end")
    p.fn(AVC, 0.3, 12, cls="c3", label="AVC", at=(12, AVC(12)), dx=-4, dy=14, anchor="end")
    p.fn(lambda q: F_ / q, 2.2, 12, cls="c4 thin", label="AFC", at=(12, F_ / 12), dx=-4, dy=-6, anchor="end")
    # min AVC at q=5 (AVC'=-2+0.4q=0) value 7 ; min ATC solve numerically
    qa = min((ATC(q / 1000), q / 1000) for q in range(2000, 12000))[1]
    p.dot(5, AVC(5), "min AVC = MC", dx=-6, dy=18, anchor="middle")
    p.dot(qa, ATC(qa), "min ATC = MC", dx=8, dy=-8)
    p.xtick(5, "5").xtick(qa, f"{qa:.1f}")
    return p.svg("U-shaped average cost curves with marginal cost passing through the minimum of AVC and ATC.")


@fig("pc_sr")
def _():
    F_, VC, MC, AVC, ATC = cubic_costs()
    P = 20
    q = (4 + math.sqrt(16 - 4 * 0.6 * (12 - P))) / 1.2  # MC = P
    p = Plot(12, 30, "Output of the firm, q", "Price, cost (₹)")
    p.poly([(0, ATC(q)), (q, ATC(q)), (q, P), (0, P)], cls="sh-profit", label="economic profit")
    p.fn(MC, 0.3, 11.5, cls="c2", label="MC", at=(10.6, MC(10.6)), dx=-8, anchor="end")
    p.fn(ATC, 2.2, 12, cls="c1", label="ATC", at=(12, ATC(12)), dx=-4, dy=-8, anchor="end")
    p.fn(AVC, 0.3, 12, cls="c3", label="AVC", at=(12, AVC(12)), dx=-4, dy=14, anchor="end")
    p.hline(P, 0, 12, cls="c4")
    p.text(0.3, P, "P = MR = AR", cls="lbl c4-t", dy=-6)
    p.dot(q, P, "MR = MC", dx=8, dy=-6)
    p.drop(q, P, xl=f"q* ≈ {q:.1f}")
    p.ytick(P, "20").ytick(ATC(q), f"ATC ≈ {ATC(q):.1f}")
    return p.svg("Short-run competitive firm: produces where P = MC; profit is the shaded rectangle (P − ATC) times q.")


@fig("pc_shutdown")
def _():
    F_, VC, MC, AVC, ATC = cubic_costs()
    p = Plot(12, 30, "Output of the firm, q", "Price, cost (₹)")
    p.fn(MC, 0.3, 11.5, cls="c2", label="MC", at=(10.6, MC(10.6)), dx=-8, anchor="end")
    p.fn(ATC, 2.2, 12, cls="c1", label="ATC", at=(12, ATC(12)), dx=-4, dy=-8, anchor="end")
    p.fn(AVC, 0.3, 12, cls="c3", label="AVC", at=(12, AVC(12)), dx=-4, dy=14, anchor="end")
    qa = min((ATC(q / 1000), q / 1000) for q in range(2000, 12000))[1]
    # firm supply curve: MC above min AVC
    p.fn(MC, 5, 11.5, cls="supply-hl")
    p.dot(5, 7, "shutdown point (min AVC)", dx=-6, dy=20, anchor="middle")
    p.dot(qa, ATC(qa), "break-even (min ATC)", dx=8, dy=-8)
    p.hline(7, 0, 5, cls="guide")
    p.hline(ATC(qa), 0, qa, cls="guide")
    p.ytick(7, "7").ytick(ATC(qa), f"{ATC(qa):.1f}")
    p.text(9.2, 25, "firm's SR supply curve", cls="lbl small strong", anchor="end")
    return p.svg("The competitive firm's short-run supply curve is the part of MC above minimum AVC.")


@fig("pc_lr")
def _():
    # firm with ATC = 100/q + 4 + q, min at q=10, ATC=24 ; market Qd = 1000 - 20P
    p1 = Plot(20, 50, "Firm output, q", "Price (₹)", h=340, w=420, mr=20)
    ATC = lambda q: 100 / q + 4 + q
    MC = lambda q: 4 + 2 * q
    p1.fn(ATC, 2.6, 20, cls="c1", label="ATC", at=(19, ATC(19)), dx=-4, dy=-6, anchor="end")
    p1.fn(MC, 0, 20, cls="c2", label="MC", at=(18, MC(18)), dx=-8, anchor="end")
    p1.hline(27, 0, 20, cls="c4 dashed")
    p1.text(0.4, 27, "P₀ = 27 (SR profit)", cls="lbl c4-t small", dy=-6)
    p1.hline(24, 0, 20, cls="c4")
    p1.text(0.4, 24, "P_LR = 24 = min ATC", cls="lbl c4-t small", dy=16)
    p1.dot(11.5, 27, "")
    p1.dot(10, 24, "")
    p1.xtick(10, "10").xtick(11.5, "11.5")
    p2 = Plot(800, 50, "Market output, Q", "Price (₹)", h=340, w=420, mr=20)
    Dm = lambda Q: (1000 - Q) / 20
    p2.fn(Dm, 300, 800, cls="c1", label="D", at=(800, Dm(800)), dx=-4, dy=-8, anchor="end")
    p2.fn(lambda Q: 4 + 2 * Q / 40, 0, 800, cls="c2", label="S₀", at=(560, 4 + 2 * 560 / 40), dx=-6, dy=-6, anchor="end")
    p2.fn(lambda Q: 4 + 2 * Q / 52, 0, 800, cls="c2 dashed", label="S₁", at=(800, 4 + 2 * 800 / 52), dx=-4, dy=14, anchor="end")
    p2.hline(24, 0, 800, cls="c4")
    p2.dot(460, 27, "")
    p2.dot(520, 24, "")
    p2.xtick(460, "460").xtick(520, "520")
    p2.ytick(27, "27").ytick(24, "24")
    return pair(p1.svg("Long run firm: entry drives price down to minimum ATC, profits to zero."),
                p2.svg("Market: entry shifts supply right until price equals minimum ATC."))


@fig("lrac")
def _():
    p = Plot(10, 10, "Output, Q", "Long-run average cost")
    f = lambda q: 3 + 0.55 * max(0, abs(q - 5) - 1.2) ** 2
    p.fn(f, 0.4, 9.8, cls="c1", label="LRAC", at=(9.6, f(9.6)), dx=-6, anchor="end")
    p.vline(3.8, 0, 9.5).vline(6.2, 0, 9.5)
    p.text(1.9, 1.2, "IRS", cls="lbl strong", anchor="middle")
    p.text(1.9, 0.5, "economies of scale", cls="lbl small", anchor="middle")
    p.text(5, 1.2, "CRS", cls="lbl strong", anchor="middle")
    p.text(8.1, 1.2, "DRS", cls="lbl strong", anchor="middle")
    p.text(8.1, 0.5, "diseconomies", cls="lbl small", anchor="middle")
    p.xtick(5, "MES →")
    return p.svg("U-shaped long-run average cost: falling with increasing returns to scale, flat with constant returns, rising with decreasing returns.")


# =============================================================================
# LECTURE 8 - MONOPOLY AND OLIGOPOLY
# =============================================================================

@fig("monopoly")
def _():
    a, c = 100, 20
    p = Plot(100, 110)
    p.poly([(0, 60), (40, 60), (40, 20), (0, 20)], cls="sh-profit", label="monopoly profit = 1600")
    p.poly([(0, 100), (40, 60), (0, 60)], cls="sh-cs", label="CS = 800", at=(12, 72))
    p.poly([(40, 60), (80, 20), (40, 20)], cls="sh-dwl", label="DWL = 800", at=(52, 33))
    p.fn(lambda q: a - q, 0, 100, cls="c1")
    p.text(25, 75, "D = AR: P = 100 − Q", cls="lbl c1-t", dx=8, dy=-4)
    p.fn(lambda q: a - 2 * q, 0, 50, cls="c3", label="MR = 100 − 2Q", at=(46, 8), dx=6, dy=-2)
    p.hline(20, 0, 100, cls="c2")
    p.text(2, 20, "MC = AC = 20", cls="lbl c2-t", dy=16)
    p.dot(40, 60, "Mₘ", dx=8, dy=-6)
    p.dot(40, 20, "MR = MC", dx=-6, dy=18, anchor="end")
    p.dot(80, 20, "competitive", dx=8, dy=-8)
    p.drop(40, 60, xl="Qm = 40", yl="Pm = 60")
    p.xtick(80, "Qc = 80")
    return p.svg("Monopoly with P = 100 − Q and MC = 20: output 40, price 60, profit 1600, deadweight loss 800.")


@fig("price_disc")
def _():
    p = Plot(100, 110)
    p.poly([(0, 100), (80, 20), (0, 20)], cls="sh-profit", label="profit = all surplus = 3200", at=(22, 45))
    p.fn(lambda q: 100 - q, 0, 100, cls="c1")
    p.text(30, 70, "D: P = 100 − Q", cls="lbl c1-t", dx=8, dy=-4)
    p.hline(20, 0, 100, cls="c2")
    p.text(2, 20, "MC = 20", cls="lbl c2-t", dy=16)
    p.dot(80, 20, "Q = 80 (efficient)", dx=4, dy=-10)
    p.xtick(80, "80")
    return p.svg("First-degree price discrimination: each unit sold at the buyer's reservation price; output is efficient and the firm captures all surplus.")


@fig("cournot")
def _():
    p = Plot(95, 95, "Firm a's output, qa", "Firm b's output, qb")
    p.line((0, 45), (45, 0), cls="c4 thin dashed")
    p.line((0, 90), (90, 0), cls="c3 thin dashed")
    p.line((45, 0), (0, 90), cls="c1")
    p.line((0, 45), (90, 0), cls="c2")
    p.text(5, 80, "Ra: qa = (90 − qb)/2", cls="lbl c1-t", dx=8)
    p.text(75, 7.5, "Rb: qb = (90 − qa)/2", cls="lbl c2-t", dy=18, anchor="end")
    p.dot(30, 30, "Cournot–Nash", dx=8, dy=-8)
    p.dot(45, 22.5, "Stackelberg", dx=8, dy=4)
    p.drop(30, 30, xl="30", yl="30")
    p.xtick(45, "45").ytick(45, "45").xtick(90, "90").ytick(90, "90")
    return p.svg("Cournot reaction functions intersect at (30, 30). The Stackelberg leader picks the point (45, 22.5) on the follower's reaction function.")


# =============================================================================
# WELFARE ECONOMICS
# =============================================================================

def base_sd(p, d_label="Demand (MB)", s_label="Supply (MC)"):
    p.fn(D, 0, 10, cls="c1", label=d_label, at=(8.4, D(8.4)), dy=-8)
    p.fn(S, 0, 10, cls="c2", label=s_label, at=(8.8, S(8.8)), dx=-6, dy=-8, anchor="end")


@fig("surplus")
def _():
    p = Plot(10, 12)
    p.poly([(0, 10), (4, 6), (0, 6)], cls="sh-cs", label="CS = 8", at=(1.4, 7.4))
    p.poly([(0, 2), (4, 6), (0, 6)], cls="sh-ps", label="PS = 8", at=(1.4, 4.7))
    base_sd(p)
    p.dot(4, 6, "E", dx=8, dy=-2)
    p.drop(4, 6, xl="4", yl="6")
    p.ytick(10, "10").ytick(2, "2")
    return p.svg("Consumer surplus is the triangle between demand and price; producer surplus the triangle between price and supply. Each equals 8, total surplus 16.")


@fig("tax")
def _():
    p = Plot(10, 12)
    p.poly([(0, 10), (3, 7), (0, 7)], cls="sh-cs", label="CS = 4.5", at=(1.1, 7.8))
    p.poly([(0, 7), (3, 7), (3, 5), (0, 5)], cls="sh-tax", label="tax revenue = 6", at=(1.5, 6))
    p.poly([(0, 2), (3, 5), (0, 5)], cls="sh-ps", label="PS = 4.5", at=(1.1, 4.1))
    p.poly([(3, 7), (4, 6), (3, 5)], cls="sh-dwl", label="", at=(3.35, 6))
    base_sd(p)
    p.fn(lambda q: 4 + q, 0, 8, cls="c2 dashed", label="S + tax", at=(6, 10), dx=-8, anchor="end")
    p.text(4.25, 6.3, "DWL = 1", cls="lbl small strong")
    p.drop(3, 7, xl="3", yl="Pb = 7")
    p.hline(5, 0, 3, cls="guide")
    p.ytick(5, "Ps = 5")
    p.xtick(4, "4")
    return p.svg("A tax of 2 per unit: buyers pay 7, sellers keep 5, quantity falls from 4 to 3; deadweight loss 1.")


@fig("ceiling")
def _():
    p = Plot(10, 12)
    p.region(D, lambda q: 4, 0, 2, cls="sh-cs", label="CS = 10", at=(0.9, 6.2))
    p.poly([(0, 2), (2, 4), (0, 4)], cls="sh-ps", label="PS = 2", at=(0.7, 3.4))
    p.poly([(2, 8), (4, 6), (2, 4)], cls="sh-dwl", label="DWL = 4", at=(2.7, 6))
    base_sd(p)
    p.hline(4, 0, 10, cls="c4")
    p.text(9.8, 4, "price cap = 4", cls="lbl c4-t", dy=-6, anchor="end")
    p.line((2, 4), (6, 4), cls="gap")
    p.text(4, 4, "shortage = 4", cls="lbl small", dy=18, anchor="middle")
    p.drop(2, 8, xl="2", yl="8")
    p.xtick(6, "6")
    return p.svg("A price ceiling of 4 cuts quantity to 2 and creates a shortage of 4 and deadweight loss of 4.")


@fig("externality")
def _():
    p = Plot(10, 12, "Quantity, Q", "Price, cost (₹)")
    p.poly([(3, 7), (4, 8), (4, 6)], cls="sh-dwl", label="", at=(3.7, 7))
    p.fn(D, 0, 10, cls="c1", label="MPB = MSB (demand)", at=(7.4, D(7.4)), dy=-8)
    p.fn(S, 0, 10, cls="c2", label="MPC (supply)", at=(9.3, S(9.3)), dx=-6, dy=14, anchor="end")
    p.fn(lambda q: 4 + q, 0, 8, cls="c4", label="MSC = MPC + MEC", at=(7.6, 11.6), dx=-6, anchor="end")
    p.dot(4, 6, "market", dx=8, dy=10)
    p.dot(3, 7, "social optimum", dx=-8, dy=-12, anchor="end")
    p.drop(4, 6, xl="Qm = 4", yl="6")
    p.drop(3, 7, xl="Q* = 3", yl="7")
    p.text(4.2, 7.1, "DWL = 1", cls="lbl small strong")
    p.line((5.5, 7.5), (5.5, 9.5), cls="gap")
    p.text(5.6, 8.5, "MEC = 2", cls="lbl small", dx=4)
    return p.svg("Negative externality: market output 4 exceeds socially optimal output 3 where marginal social cost equals marginal benefit.")


@fig("ppf_utility")
def _():
    p = Plot(10, 10, "Person 1's well-being", "Person 2's well-being")
    f = lambda x: math.sqrt(max(0, 81 - x * x))
    p.poly([(3.2, 3.0), (3.2, f(3.2)), (math.sqrt(81 - 9), 3.0)], cls="sh-cs", label="Pareto improvements", at=(4.6, 5.2))
    p.fn(f, 0, 9, cls="c1")
    p.text(1.0, f(1.0), "Pareto frontier (efficient)", cls="lbl c1-t", dy=-10)
    p.dot(3.2, 3.0, "Z (inefficient)", dx=8, dy=6)
    p.dot(9, 0, "one person has all", dx=-4, dy=-10, anchor="end")
    p.dot(6.36, 6.36, "equal split", dx=10, dy=0)
    return p.svg("Utility possibility frontier: points on the frontier are Pareto efficient; points inside can be improved for both.")


@fig("mac_trade")
def _():
    p = Plot(45, 70, "Abatement, A (tonnes)", "Marginal abatement cost (₹)")
    p.fn(lambda a: a, 0, 45, cls="c1", label="MAC₁ = A₁", at=(44, 44), dx=-6, dy=-8, anchor="end")
    p.fn(lambda a: 3 * a, 0, 23, cls="c2", label="MAC₂ = 3A₂", at=(22, 66), dx=-6, anchor="end")
    p.hline(30, 0, 45, cls="c4")
    p.text(44, 30, "permit price = 30", cls="lbl c4-t", dy=-6, anchor="end")
    p.dot(30, 30, "firm 1 abates 30", dx=6, dy=16)
    p.dot(10, 30, "firm 2 abates 10", dx=-6, dy=-8, anchor="end")
    p.drop(20, 20, xl="20")
    p.dot(20, 20, "uniform rule: MAC₁ = 20", dx=8, dy=14)
    p.dot(20, 60, "MAC₂ = 60", dx=8)
    p.layers["guide"].append(f'<line class="guide" x1="{p.px(20):.1f}" y1="{p.py(20):.1f}" x2="{p.px(20):.1f}" y2="{p.py(60):.1f}"/>')
    p.xtick(10, "10").xtick(30, "30")
    return p.svg("Cap and trade: trading equalises marginal abatement costs at the permit price.")


@fig("commons")
def _():
    p = Plot(90, 110, "Number of boats, N", "Value per boat (₹)")
    p.fn(lambda n: 100 - n, 0, 90, cls="c1")
    p.text(62, 38, "AP = 100 − N", cls="lbl c1-t", dx=6, dy=-6)
    p.fn(lambda n: 100 - 2 * n, 0, 50, cls="c3")
    p.text(25, 50, "MP = 100 − 2N", cls="lbl c3-t", dx=8)
    p.hline(20, 0, 90, cls="c2")
    p.text(1, 20, "cost per boat = 20", cls="lbl c2-t", dy=-6)
    p.dot(80, 20, "open access N = 80", dx=-6, dy=18, anchor="end")
    p.dot(40, 20, "N* = 40", dx=-6, dy=18, anchor="end")
    p.xtick(40, "40").xtick(80, "80")
    return p.svg("Open access fishery: entry continues until average product equals cost (80 boats) versus the efficient 40 where marginal product equals cost.")


def all_figures():
    return {k: v() for k, v in F.items()}


if __name__ == "__main__":
    figs = all_figures()
    print(len(figs), "figures:", ", ".join(figs))
