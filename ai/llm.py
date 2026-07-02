"""
ai/llm.py
=========
Módulo unificado de acesso a LLMs — suporta Gemini, OpenAI e Anthropic.

A escolha do provedor é feita via variável de ambiente LLM_PROVIDER.
Isso permite trocar de LLM sem mudar uma linha do código do RAG.

Provedores suportados:
  - "gemini"    → Google Gemini API (GRATUITO no Free Tier)
                  Limite: 1.500 requisições/dia, 15 req/min
                  Modelo padrão: gemini-2.0-flash-lite
                  Cadastro: https://aistudio.google.com/apikey

  - "openai"    → OpenAI GPT (pago, mas gpt-4o-mini é barato)
                  Modelo padrão: gpt-4o-mini

  - "anthropic" → Anthropic Claude (pago)
                  Modelo padrão: claude-3-5-haiku-20241022

Por que Gemini Free Tier é suficiente para este projeto?
  - O RAG faz UMA chamada por pergunta do usuário
  - O dashboard não tem usuários simultâneos (é pessoal)
  - 1.500 req/dia = ~62 perguntas por hora — mais que suficiente
  - gemini-2.0-flash-lite tem excelente qualidade para sumarização de notícias

Uso:
    from ai.llm import get_llm_response
    response = get_llm_response("Qual foi o desempenho da PETR4 esta semana?", context)
"""

from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# Lê configurações do .env
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini").lower()
LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-2.0-flash-lite")

# Prompt de sistema padrão para o RAG financeiro
SYSTEM_PROMPT = """You are FinSight, an AI financial analyst assistant.
You answer questions about stock market data based exclusively on the context provided.
The context contains recent market data and news articles from the user's own data pipeline.

Rules:
- Only use information from the provided context. Do not hallucinate.
- Cite the news sources when referencing specific articles.
- If the context doesn't contain enough information, say so clearly.
- Answer in the same language the question was asked (Portuguese or English).
- Be concise and objective. This is for investment analysis, not entertainment.
"""


def get_llm_response(
    question: str,
    context: str,
    system_prompt: Optional[str] = None,
) -> str:
    """
    Envia uma pergunta + contexto para o LLM configurado e retorna a resposta.

    Esta é a função central do RAG — chamada uma única vez por pergunta.
    O contexto é montado pelo módulo rag.py com os chunks mais relevantes
    recuperados do pgvector.

    Args:
        question:      Pergunta do usuário em linguagem natural.
        context:       Texto com notícias e dados relevantes (do retrieval).
        system_prompt: Prompt de sistema customizado (default: SYSTEM_PROMPT).

    Returns:
        Resposta do LLM como string.

    Raises:
        ValueError: Se o provedor não for suportado ou a API key estiver faltando.
        Exception:  Erros de API (rate limit, timeout, etc.).

    Example:
        context = "PETR4 closed at R$ 38.50, up 2.3%. News: Petrobras reported..."
        answer = get_llm_response("Como foi a PETR4 hoje?", context)
    """
    system = system_prompt or SYSTEM_PROMPT

    # Monta o prompt completo com o contexto injetado
    full_prompt = f"""<context>
{context}
</context>

<question>
{question}
</question>

Based on the context above, answer the question. If the context is insufficient, say so."""

    logger.info(f"Calling LLM provider: {LLM_PROVIDER} / model: {LLM_MODEL}")

    if LLM_PROVIDER == "gemini":
        return _call_gemini(full_prompt, system)
    elif LLM_PROVIDER == "openai":
        return _call_openai(full_prompt, system)
    elif LLM_PROVIDER == "anthropic":
        return _call_anthropic(full_prompt, system)
    elif LLM_PROVIDER == "groq":
        return _call_groq(full_prompt, system)
    else:
        raise ValueError(
            f"Unsupported LLM_PROVIDER: '{LLM_PROVIDER}'. "
            "Valid options: gemini, openai, anthropic, groq"
        )


# =============================================================================
# Implementações por provedor
# =============================================================================

def _call_gemini(prompt: str, system: str) -> str:
    """
    Chama a Google Gemini API.

    Biblioteca: google-generativeai (instalar com: pip install google-generativeai)
    Free Tier: https://ai.google.dev/pricing
      - gemini-2.0-flash-lite: 1.500 req/dia grátis
      - gemini-1.5-flash:      1.500 req/dia grátis
      - Sem necessidade de cartão de crédito para o tier gratuito

    Documentação: https://ai.google.dev/api/python/google/generativeai
    """
    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError(
            "google-generativeai not installed. Run:\n"
            "  .venv\\Scripts\\python.exe -m pip install google-generativeai"
        )

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.startswith("<"):
        raise ValueError(
            "GEMINI_API_KEY not set in .env. "
            "Get your free key at: https://aistudio.google.com/apikey"
        )

    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(
        model_name=LLM_MODEL,
        system_instruction=system,
    )

    response = model.generate_content(prompt)
    return response.text


def _call_openai(prompt: str, system: str) -> str:
    """
    Chama a OpenAI API (gpt-4o-mini, gpt-4o, etc.).

    Biblioteca: openai (pip install openai)
    Preços: https://openai.com/pricing
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError(
            "openai not installed. Run:\n"
            "  .venv\\Scripts\\python.exe -m pip install openai"
        )

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("<"):
        raise ValueError("OPENAI_API_KEY not set in .env")

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.3,   # Baixo = mais factual, menos criativo (melhor pra finanças)
        max_tokens=1024,
    )
    return response.choices[0].message.content


def _call_anthropic(prompt: str, system: str) -> str:
    """
    Chama a API da Anthropic (Claude).

    Biblioteca: anthropic (pip install anthropic)
    Preços: https://www.anthropic.com/pricing
    """
    try:
        import anthropic
    except ImportError:
        raise ImportError(
            "anthropic not installed. Run:\n"
            "  .venv\\Scripts\\python.exe -m pip install anthropic"
        )

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key.startswith("<"):
        raise ValueError("ANTHROPIC_API_KEY not set in .env")

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=LLM_MODEL,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _call_groq(prompt: str, system: str) -> str:
    """
    Chama a API do Groq (Llama 3.3 70B, Mixtral, etc.).

    Biblioteca: groq (pip install groq)
    Free Tier: https://console.groq.com — sem cartão, generoso
    Modelo padrão: llama-3.3-70b-versatile
    """
    try:
        from groq import Groq
    except ImportError:
        raise ImportError(
            "groq not installed. Run:\n"
            "  .venv\\Scripts\\python.exe -m pip install groq"
        )

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key.startswith("<"):
        raise ValueError("GROQ_API_KEY not set in .env. Get your free key at: https://console.groq.com")

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.3,
        max_tokens=1024,
    )
    return response.choices[0].message.content


# =============================================================================
# Teste rápido — roda direto: python ai/llm.py
# =============================================================================

if __name__ == "__main__":
    print(f"Testing LLM provider: {LLM_PROVIDER} / {LLM_MODEL}")
    print("-" * 50)

    test_context = """
    PETR4 closed at R$ 38.50 today, up 2.3%.
    News: Petrobras announced record quarterly profits due to high oil prices.
    VALE3 dropped 1.1% to R$ 62.10 amid concerns over iron ore demand from China.
    """
    test_question = "Qual foi o desempenho das ações de petróleo e mineração hoje?"

    try:
        answer = get_llm_response(test_question, test_context)
        print(f"Answer:\n{answer}")
    except Exception as e:
        print(f"Error: {e}")
