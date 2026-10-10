"""Shared helpers for the prop tools: HTTP fetch and probability maths (stdlib only)."""
import json
import math
import urllib.request

USER_AGENT = "Mozilla/5.0 (sports-betting-claude prop tools)"


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


# ---------- odds ----------

def american_to_decimal(odds):
    return 1 + (odds / 100 if odds > 0 else 100 / -odds)


def parse_odds(text):
    """Accept American (+120 / -150), decimal (2.2) or fractional (6/5)."""
    text = str(text).strip()
    if "/" in text:
        num, den = text.split("/")
        return float(num) / float(den) + 1
    value = float(text)
    if text.startswith(("+", "-")) or abs(value) >= 100:
        return american_to_decimal(value)
    return value


def decimal_to_american(dec):
    if dec >= 2:
        return f"+{round((dec - 1) * 100)}"
    return f"{round(-100 / (dec - 1))}"


# ---------- distributions ----------

def poisson_pmf(k, lam):
    return math.exp(-lam) * lam ** k / math.factorial(k)


def negbin_pmf(k, mean, var):
    """Negative binomial parameterised by mean and variance (var > mean)."""
    r = mean ** 2 / (var - mean)
    p = r / (r + mean)
    return math.exp(math.lgamma(k + r) - math.lgamma(r) - math.lgamma(k + 1)
                    + r * math.log(p) + k * math.log(1 - p))


def count_p_over(line, mean, var=None):
    """P(X > line) for a count stat. Half-point lines only (0.5, 1.5, ...)."""
    threshold = math.floor(line)  # X > 1.5  <=>  X >= 2  <=>  1 - P(X <= 1)
    if var is not None and var > mean * 1.05:
        cdf = sum(negbin_pmf(k, mean, var) for k in range(threshold + 1))
    else:
        cdf = sum(poisson_pmf(k, mean) for k in range(threshold + 1))
    return 1 - cdf


def normal_p_over(line, mean, sd):
    return 0.5 * math.erfc((line - mean) / (sd * math.sqrt(2)))


def mean_var(values):
    n = len(values)
    if n == 0:
        return 0.0, 0.0
    m = sum(values) / n
    v = sum((x - m) ** 2 for x in values) / (n - 1) if n > 1 else m
    return m, v
