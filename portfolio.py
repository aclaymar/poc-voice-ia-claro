# portfolio.py - Integração com JSON de Portfólio Residencial (São Paulo)
# Fonte: https://static.net.com.br/json/assine/assine_v3_sao_paulo_mobile.json

import requests
import json
import time
from typing import Optional

PORTFOLIO_URL = "https://static.net.com.br/json/assine/assine_v3_sao_paulo_mobile.json"
CACHE_TTL_SEGUNDOS = 3600  # 1 hora

_cache = {"data": None, "timestamp": 0}


def _fetch_portfolio() -> Optional[dict]:
    """Busca o JSON do portfólio com cache TTL de 1 hora."""
    agora = time.time()
    if _cache["data"] and (agora - _cache["timestamp"]) < CACHE_TTL_SEGUNDOS:
        return _cache["data"]
    try:
        resp = requests.get(PORTFOLIO_URL, timeout=10)
        resp.raise_for_status()
        _cache["data"] = resp.json()
        _cache["timestamp"] = agora
        return _cache["data"]
    except Exception:
        return _cache["data"]  # retorna cache desatualizado se falhar


def buscar_ofertas(
    cep: Optional[str] = None,
    perfil_cliente: str = "prospect",
    tem_gpon: bool = False,
) -> str:
    """
    Busca e formata as ofertas residenciais de São Paulo para o LLM.

    Args:
        cep: CEP do cliente (para filtro futuro)
        perfil_cliente: "base" (já cliente) ou "prospect" (novo cliente)
        tem_gpon: True se o endereço suporta GPON

    Returns:
        String formatada com as ofertas disponíveis para incluir no contexto da IA.
    """
    dados = _fetch_portfolio()

    if not dados:
        return (
            "Portfólio residencial: no momento não consigo carregar os planos disponíveis. "
            "Oriente o cliente a consultar claro.com.br ou ligar para 0800 383 2121."
        )

    try:
        linhas = [
            f"PORTFÓLIO RESIDENCIAL — SÃO PAULO (Perfil: {perfil_cliente.upper()})",
            "=" * 60,
        ]

        # Tenta localizar produtos no JSON (estrutura pode variar)
        produtos = _extrair_produtos(dados, perfil_cliente, tem_gpon)

        if produtos:
            for p in produtos[:8]:  # limite para não sobrecarregar o contexto
                linhas.append(p)
        else:
            linhas.append(
                "Planos disponíveis: consultar claro.com.br ou 0800 383 2121"
            )

        if not tem_gpon:
            linhas.append(
                "\nATENÇÃO: Endereço sem TAG GPON — não oferecer planos com tecnologia GPON."
            )

        return "\n".join(linhas)

    except Exception:
        return (
            "Portfólio residencial: erro ao processar planos. "
            "Oriente o cliente a consultar claro.com.br ou ligar para 0800 383 2121."
        )


def _extrair_produtos(dados: dict, perfil: str, tem_gpon: bool) -> list:
    """Extrai lista de produtos formatados do JSON do portfólio."""
    resultados = []

    # Tenta diferentes chaves comuns em JSONs de portfólio Claro
    candidatos = []
    for chave in ["produtos", "planos", "offers", "items", "data", "plans"]:
        if chave in dados:
            candidatos = dados[chave]
            break

    if isinstance(dados, list):
        candidatos = dados

    for item in candidatos:
        if not isinstance(item, dict):
            continue

        # Filtra por perfil (base vs prospect)
        tags = item.get("tags", []) or item.get("tag", [])
        if isinstance(tags, str):
            tags = [tags]
        tags_lower = [str(t).lower() for t in tags]

        # Pula produto GPON se endereço não tem suporte
        if not tem_gpon and any("gpon" in t for t in tags_lower):
            continue

        # Filtra por perfil
        if perfil == "base" and any("prospect" in t for t in tags_lower):
            continue
        if perfil == "prospect" and any(
            t in tags_lower for t in ["base_only", "base-only", "retencao"]
        ):
            continue

        nome = (
            item.get("nome")
            or item.get("name")
            or item.get("titulo")
            or item.get("title")
            or "Plano sem nome"
        )
        preco = (
            item.get("preco")
            or item.get("price")
            or item.get("valor")
            or item.get("value")
            or ""
        )
        velocidade = (
            item.get("velocidade")
            or item.get("speed")
            or item.get("internet")
            or ""
        )
        descricao = item.get("descricao") or item.get("description") or ""

        linha = f"- {nome}"
        if velocidade:
            linha += f" | {velocidade}"
        if preco:
            linha += f" | R$ {preco}"
        if descricao:
            linha += f" | {str(descricao)[:80]}"
        resultados.append(linha)

    return resultados


def verificar_viabilidade_gpon(cep: str) -> bool:
    """
    Placeholder: verifica se um CEP tem cobertura GPON.
    Em produção, isso seria uma chamada à API de viabilidade da Claro.
    """
    # TODO: integrar com API de viabilidade técnica da Claro
    # Por ora, retorna False (conservador — não oferece GPON sem confirmação)
    return False


def resumo_para_contexto(perfil_cliente: str = "prospect") -> str:
    """
    Retorna um resumo curto do portfólio para incluir no system prompt.
    Usado quando não temos o CEP do cliente ainda.
    """
    return (
        f"PORTFÓLIO RESIDENCIAL SP ({perfil_cliente.upper()}):\n"
        "Para apresentar planos residenciais, preciso do CEP do cliente para verificar "
        "disponibilidade e tecnologia (GPON ou HFC) no endereço. "
        "Só ofereço GPON se o sistema confirmar a TAG gpon para o endereço. "
        "Acesse claro.com.br ou ligue 0800 383 2121 para consulta completa."
    )
