"""Provider-agnostic completion call.

The agent defaults to ADL's own agent model so that arm P is a reproduction of
their setup rather than an approximation. From the paper's ablation section:
"Agent = gpt-5 (main), plus Gemini 2.5 Pro and the weaker gpt-5-chat"; graders
were gpt-5-mini, Claude Haiku 4.5 and Gemini 2.5 Flash (Krippendorff alpha 0.81).

Getting this axis right matters here specifically: the 97%-vs-91% error in the
original plan came from quoting the gpt-5-chat ablation as the headline. Running
a *different* agent and comparing to their number would repeat that mistake in
a subtler form.

Routing is by model-name prefix. Both providers cache a stable prefix — Anthropic
via an explicit cache_control breakpoint, OpenAI automatically — so in both cases
the per-seed nonce must be the LAST thing in the prompt.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass


@dataclass
class Completion:
    text: str
    stop_reason: str
    input_tokens: int
    output_tokens: int
    cached_tokens: int = 0
    model: str = ""


def provider_for(model: str) -> str:
    m = model.lower()
    if m.startswith(("gpt", "o1", "o3", "o4", "chatgpt")):
        return "openai"
    if m.startswith("claude"):
        return "anthropic"
    raise ValueError(
        f"Cannot infer provider for model {model!r}. Prefix it with 'gpt-'/'claude-' "
        f"or extend provider_for()."
    )


def require_key(model: str) -> None:
    """Fail early and specifically rather than deep inside a run."""
    var = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}[provider_for(model)]
    if not os.environ.get(var):
        raise RuntimeError(f"{var} is not set, required for model {model!r}.")


# --------------------------------------------------------------------------

def _anthropic(model, system, stable, nonce, max_tokens, effort) -> Completion:
    import anthropic

    client = anthropic.Anthropic()
    kwargs = dict(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": stable, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": nonce},
        ]}],
    )
    if effort:
        kwargs["output_config"] = {"effort": effort}
    r = client.messages.create(**kwargs)
    return Completion(
        text="".join(b.text for b in r.content if b.type == "text"),
        stop_reason=r.stop_reason or "",
        input_tokens=r.usage.input_tokens,
        output_tokens=r.usage.output_tokens,
        cached_tokens=getattr(r.usage, "cache_read_input_tokens", 0) or 0,
        model=r.model,
    )


# Parameter names and support vary across OpenAI model generations (reasoning
# models reject `temperature`, renamed `max_tokens` -> `max_completion_tokens`).
# Rather than hardcode a guess, drop whatever the API names in a 400 and retry.
_UNSUPPORTED = re.compile(r"'([a-z_]+)'|\"([a-z_]+)\"|`([a-z_]+)`")


def _openai(model, system, stable, nonce, max_tokens, effort) -> Completion:
    from openai import OpenAI, BadRequestError

    client = OpenAI()
    kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            # One string: OpenAI caches long stable prefixes automatically, so
            # the nonce simply goes last. No explicit breakpoint to place.
            {"role": "user", "content": f"{stable}\n\n{nonce}"},
        ],
        "max_completion_tokens": max_tokens,
    }
    if effort:
        kwargs["reasoning_effort"] = effort

    for _ in range(4):
        try:
            r = client.chat.completions.create(**kwargs)
            break
        except BadRequestError as e:
            msg = str(e)
            dropped = None
            for key in list(kwargs):
                if key in ("model", "messages"):
                    continue
                if key in msg:
                    kwargs.pop(key)
                    dropped = key
                    break
            if dropped is None and "max_completion_tokens" in kwargs:
                kwargs["max_tokens"] = kwargs.pop("max_completion_tokens")
                dropped = "max_completion_tokens->max_tokens"
            if dropped is None:
                raise
            print(f"  [llm] retrying without {dropped}")
    else:
        raise RuntimeError("Could not find an accepted parameter set for " + model)

    u = r.usage
    cached = 0
    details = getattr(u, "prompt_tokens_details", None)
    if details is not None:
        cached = getattr(details, "cached_tokens", 0) or 0
    return Completion(
        text=r.choices[0].message.content or "",
        stop_reason=r.choices[0].finish_reason or "",
        input_tokens=u.prompt_tokens,
        output_tokens=u.completion_tokens,
        cached_tokens=cached,
        model=r.model,
    )


def complete(model: str, system: str, stable: str, nonce: str = "",
             max_tokens: int = 8000, effort: str | None = None) -> Completion:
    """`stable` is cached across calls; `nonce` varies per call and goes last."""
    fn = {"anthropic": _anthropic, "openai": _openai}[provider_for(model)]
    return fn(model, system, stable, nonce, max_tokens, effort)
