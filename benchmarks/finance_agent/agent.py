import os
from typing import Dict, List, Optional, Tuple

from benchmarks.finance_agent.tools import (
    edgar_search,
    fetch_url,
    google_web_search,
    parse_html_page,
)


class FinanceAgent:
    def __init__(
        self,
        provider: str,
        model: str,
        enable_google: bool = False,
        enable_edgar: bool = False,
        serpapi_key: Optional[str] = None,
        sec_api_key: Optional[str] = None,
        user_agent: Optional[str] = None,
        max_web_pages: int = 2,
    ):
        self.provider = provider
        self.model = model
        self.enable_google = enable_google
        self.enable_edgar = enable_edgar
        self.serpapi_key = serpapi_key
        self.sec_api_key = sec_api_key
        self.user_agent = user_agent
        self.max_web_pages = max_web_pages

    def _build_context(self, question: str) -> Tuple[str, List[Dict], List[str]]:
        tool_calls = []
        sources = []
        context_parts = []

        if self.enable_google:
            tool_calls.append({"tool": "google_web_search", "input": question})
            results = google_web_search(question, api_key=self.serpapi_key)
            for item in results[: self.max_web_pages]:
                link = item.get("link")
                if link:
                    sources.append(link)
                    try:
                        html = fetch_url(link, user_agent=self.user_agent)
                        text = parse_html_page(html)
                        context_parts.append(f"Source: {link}\n{text}")
                    except Exception:
                        continue

        if self.enable_edgar:
            tool_calls.append({"tool": "edgar_search", "input": question})
            try:
                edgar = edgar_search(question, api_key=self.sec_api_key)
                context_parts.append("EDGAR search results:\n" + str(edgar)[:3000])
            except Exception:
                pass

        context = "\n\n".join(context_parts)
        return context, tool_calls, sources

    def _call_openai(self, prompt: str) -> str:
        try:
            import openai
        except Exception as exc:
            raise RuntimeError("openai package not installed") from exc
        openai.api_key = os.getenv("OPENAI_API_KEY")
        resp = openai.ChatCompletion.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.0,
        )
        return resp.choices[0].message.content.strip()

    def _call_anthropic(self, prompt: str) -> str:
        try:
            from anthropic import Anthropic
        except Exception as exc:
            raise RuntimeError("anthropic package not installed") from exc
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        resp = client.messages.create(
            model=self.model,
            max_tokens=800,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()

    def answer(self, question: str) -> Tuple[str, List[Dict], List[str]]:
        context, tool_calls, sources = self._build_context(question)
        prompt = (
            "You are a finance QA agent. Answer the question concisely and cite sources if provided.\n\n"
            f"Question: {question}\n\n"
            f"Context:\n{context}\n"
        )
        if self.provider == "openai":
            answer = self._call_openai(prompt)
        elif self.provider == "anthropic":
            answer = self._call_anthropic(prompt)
        else:
            raise ValueError("provider must be 'openai' or 'anthropic'")
        return answer, tool_calls, sources
