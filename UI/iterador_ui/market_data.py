"""Busca de dados de mercado externos (Selic, CDI) — ver Guide/architecture.md > Roadmap.

Único módulo da UI que faz chamadas de rede para fora do protocolo de sync. Tolerante a
falha/offline por design (mesma filosofia do resto do app): qualquer erro de rede retorna
None em vez de lançar exceção, para nunca travar a UI por falta de internet.

Fonte: Banco Central do Brasil, API de séries temporais (SGS) — é a fonte oficial/primária
desses indicadores no Brasil (o próprio CDI é calculado e publicado pela B3, mas o BCB replica
a série publicamente sem exigir cadastro/chave de API, diferente da B3). Séries usadas:
- 432 ("Meta Selic definida pelo Copom") — o número comumente divulgado como "a taxa Selic"
  (ex. 14,00% a.a.). Ver Guide/decisions/0008-fetch-selic-rate-from-bcb.md.
- 4389 ("Taxa de juros - CDI anualizada base 252") — o CDI no mesmo formato "% a.a." que a
  Selic, o jeito que costuma ser divulgado/comparado (ex. "CDI a 13,90% a.a."). Escolhida em vez
  da série 12 (CDI diário, ex. "0,0517% ao dia" — tecnicamente mais precisa mas pouco legível
  pra humano) ou da 4391 (CDI mensal). Confirmado batendo com a relação conhecida
  CDI ≈ Meta Selic − 0,10 p.p. (13,90 vs. 14,00 no dia em que foi verificado — ver
  Guide/decisions/0021-cdi-history-from-bcb.md).
"""

import datetime
import json
import urllib.request
from dataclasses import dataclass

_BCB_SELIC_META_URL = (
    "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json"
)
_BCB_CDI_ANNUALIZED_URL = (
    "https://api.bcb.gov.br/dados/serie/bcdata.sgs.4389/dados/ultimos/1?formato=json"
)
_BCB_CDI_ANNUALIZED_HISTORY_URL = (
    "https://api.bcb.gov.br/dados/serie/bcdata.sgs.4389/dados"
    "?formato=json&dataInicial={inicio}&dataFinal={fim}"
)


@dataclass
class SelicRate:
    percent_per_year: float
    reference_date: str  # dd/mm/aaaa, como retornado pelo BCB


@dataclass
class CdiRate:
    percent_per_year: float
    reference_date: str  # dd/mm/aaaa, como retornado pelo BCB


def fetch_current_selic_rate(timeout: float = 5.0) -> SelicRate | None:
    """Busca a meta da taxa Selic atual (% a.a.) direto do Banco Central. Retorna None em caso
    de qualquer falha de rede/parse — nunca lança exceção (o app precisa funcionar offline)."""
    try:
        with urllib.request.urlopen(_BCB_SELIC_META_URL, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        entry = payload[0]
        return SelicRate(percent_per_year=float(entry["valor"]), reference_date=entry["data"])
    except Exception:
        return None


def fetch_current_cdi_rate(timeout: float = 5.0) -> CdiRate | None:
    """Busca o CDI anualizado atual (% a.a.) direto do Banco Central. Retorna None em caso de
    qualquer falha de rede/parse — nunca lança exceção (o app precisa funcionar offline)."""
    try:
        with urllib.request.urlopen(_BCB_CDI_ANNUALIZED_URL, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        entry = payload[0]
        return CdiRate(percent_per_year=float(entry["valor"]), reference_date=entry["data"])
    except Exception:
        return None


def fetch_cdi_history(years: int = 3, timeout: float = 10.0) -> list[tuple[str, float]] | None:
    """Histórico do CDI anualizado (% a.a.) dos últimos `years` anos, agregado por **média
    mensal** — o BCB só publica a série 4389 diária, o que dá ~750-1000 pontos em 3 anos (pesado
    de desenhar e visualmente ruidoso: muito ponto próximo de propósito não ajuda a ler a
    tendência). Retorna uma lista de (rótulo "mm/aaaa", média do mês) em ordem cronológica, ou
    None em qualquer falha de rede/parse (mesma filosofia tolerante a offline)."""
    today = datetime.date.today()
    start = today - datetime.timedelta(days=365 * years)
    url = _BCB_CDI_ANNUALIZED_HISTORY_URL.format(
        inicio=start.strftime("%d/%m/%Y"), fim=today.strftime("%d/%m/%Y"))
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None

    months: dict[str, list[float]] = {}
    month_order: list[str] = []
    for entry in payload:
        _day, month, year = entry["data"].split("/")
        month_key = f"{month}/{year}"
        if month_key not in months:
            months[month_key] = []
            month_order.append(month_key)
        months[month_key].append(float(entry["valor"]))

    return [(month_key, sum(months[month_key]) / len(months[month_key]))
            for month_key in month_order]
