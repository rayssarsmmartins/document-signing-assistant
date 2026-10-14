"""Checagens de prontidão, resumo (nó 5) e argumentos do envio (nó 6)."""

from __future__ import annotations

import hashlib
import json
import re

import jsonschema

from . import glossary
from .config import SCHEMAS_DIR, Settings

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")

# Lista de roles aceitos pelo MCP (guia de signatários, allowedRequirementRoles).
ALLOWED_ROLES = set(glossary.ROLE_LABELS) | {
    "account_holder", "accountant", "associate", "bailee", "building_manager", "collateral_provider",
    "comforter", "condominium_member", "consented", "consenting", "consenting_intervenor", "consignee",
    "co_responsible", "distracted", "distracting", "endorsee", "endorser", "first_amending",
    "guarantor_spouse", "insurance_broker", "insured", "intermediary", "intervening_guarantor", "issuer",
    "joint_debtor", "landlord", "legal_guardian", "pledged", "ratify", "real_estate_broker", "receipt",
    "resident", "second_amending", "secretary", "secured", "surveyor", "surety", "transferee",
    "transferor", "treasurer", "validator",
}


def _problem(level: str, code: str, text: str, signer: int | None = None, field: str | None = None) -> dict:
    p = {"level": level, "code": code, "text": text}
    if signer is not None:
        p["signer"] = signer
    if field:
        p["field"] = field
    return p


def check(state: dict, settings: Settings) -> list[dict]:
    """Retorna problemas. level=block impede o envio; level=warn aparece no resumo."""
    probs: list[dict] = []
    docu = state["document"]
    if not docu["can_send"]:
        probs.append(_problem("block", "document_not_sendable", docu.get("reason") or "documento não pode ser enviado"))
    if not (state.get("envelope_name") or "").strip():
        probs.append(_problem("block", "missing_title", "falta o título do envio", field="envelope_name"))
    signers = state.get("signers") or []
    if not signers:
        probs.append(_problem("block", "no_signers", "ninguém definido para assinar"))
    seen_emails: dict[str, int] = {}
    any_group = False
    for i, s in enumerate(signers):
        who = s.get("name") or f"signatário {i + 1}"
        name = (s.get("name") or "").strip()
        if len(name.split()) < 2:
            probs.append(_problem("block", "name_incomplete", f"falta o sobrenome de {who}", i, "name"))
        if any(ch.isdigit() for ch in name):
            probs.append(_problem("block", "name_has_digits", f"o nome de {who} tem números", i, "name"))
        role = s.get("role")
        if role not in ALLOWED_ROLES:
            probs.append(_problem("block", "role_invalid", f"não entendi como {who} participa do documento", i, "role"))
        auth = s.get("auth")
        if auth not in settings.allowed_auths:
            probs.append(_problem("block", "auth_not_allowed",
                                  f"forma de confirmação de identidade de {who} não está disponível", i, "auth"))
        contact = glossary.AUTH_CONTACT.get(auth or "", "email")
        email = (s.get("email") or "").strip()
        phone = re.sub(r"\D", "", s.get("phone") or "")
        if contact == "email":
            if not email:
                probs.append(_problem("block", "missing_email", f"falta o e-mail de {who}", i, "email"))
            elif not EMAIL_RE.match(email):
                probs.append(_problem("block", "invalid_email", f"o e-mail de {who} parece incorreto ({email})", i, "email"))
        if contact == "phone":
            if not phone:
                probs.append(_problem("block", "missing_phone", f"falta o celular de {who}", i, "phone"))
            elif not 10 <= len(phone) <= 11:
                probs.append(_problem("block", "invalid_phone", f"o celular de {who} precisa ter DDD + número", i, "phone"))
        if email and s.get("source") == "extracted" and not s.get("email_evidence"):
            probs.append(_problem("block", "email_without_evidence",
                                  f"o e-mail de {who} não foi encontrado no documento nem informado por você", i, "email"))
        if s.get("source") == "extracted" and s.get("confidence") == "low":
            probs.append(_problem("warn", "low_confidence", f"confira {who}: não tenho certeza dessa leitura", i))
        if email:
            key = email.lower()
            if key in seen_emails:
                probs.append(_problem("warn", "duplicate_email",
                                      f"{who} e {signers[seen_emails[key]]['name']} estão com o mesmo e-mail", i, "email"))
            seen_emails[key] = i
        if (s.get("group") or 1) > 1:
            any_group = True
    if any_group and not settings.send_group:
        probs.append(_problem("warn", "order_not_supported",
                              "ainda não consigo garantir ordem de assinatura: todos vão receber ao mesmo tempo"))
    return probs


def blocking(probs: list[dict]) -> list[dict]:
    return [p for p in probs if p["level"] == "block"]


def _canonical_content(state: dict, settings: Settings) -> dict:
    return {
        "document_sha256": state["document"]["sha256"],
        "envelope_name": (state.get("envelope_name") or "").strip(),
        "message": (state.get("message") or "").strip(),
        "send_group": settings.send_group,
        "signers": [
            {
                "name": (s.get("name") or "").strip(),
                "email": (s.get("email") or "").strip().lower(),
                "phone": re.sub(r"\D", "", s.get("phone") or ""),
                "role": s.get("role"),
                "auth": s.get("auth"),
                "group": s.get("group") or 1,
            }
            for s in state.get("signers") or []
        ],
    }


def content_hash(state: dict, settings: Settings) -> str:
    raw = json.dumps(_canonical_content(state, settings), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def _ordered(signers: list[dict]) -> list[tuple[int, dict]]:
    return sorted(enumerate(signers), key=lambda t: ((t[1].get("group") or 1), t[0]))


def render_summary(state: dict, settings: Settings) -> tuple[str, str, list[dict]]:
    """Retorna (texto do resumo em pt-BR, hash, problemas)."""
    probs = check(state, settings)
    h = content_hash(state, settings)
    d = state["document"]
    pages = f", {d['pages']} página{'s' if d['pages'] != 1 else ''}" if d.get("pages") else ""
    title = (state.get("envelope_name") or "").strip() or d["filename"]
    lines = [f"📄 {title} ({d['filename']}{pages})", "", "Quem vai assinar:"]
    signers = state.get("signers") or []
    groups = {s.get("group") or 1 for s in signers}
    show_order = settings.send_group and len(groups) > 1
    warn_by_signer = {p["signer"] for p in probs if p.get("signer") is not None}
    for n, (i, s) in enumerate(_ordered(signers), start=1):
        contact = glossary.AUTH_CONTACT.get(s.get("auth") or "", "email")
        c = s.get("email") if contact == "email" else s.get("phone")
        c = f" ({c})" if c else " (contato pendente)"
        prefix = f"{s.get('group') or 1}º" if show_order else f"{n}."
        flag = "  ⚠ confira" if i in warn_by_signer else ""
        rep = f", pela {s['represents']}" if s.get("represents") else ""
        lines.append(f"  {prefix} {s.get('name')}{c} — {glossary.role_label(s.get('role') or '')}{rep}{flag}")
    if not signers:
        lines.append("  (ninguém ainda)")
    auths = sorted({s.get("auth") for s in signers if s.get("auth")})
    if auths:
        lines += ["", "Confirmação de identidade: " + ", ".join(glossary.auth_label(a) for a in auths)]
    if state.get("message"):
        msg = state["message"].strip()
        lines.append(f'Mensagem: "{msg if len(msg) <= 160 else msg[:157] + "…"}"')
    others = state.get("mentioned_non_signers") or []
    if others:
        lines.append("Também citados no documento, mas sem assinar: " + ", ".join(o["name"] for o in others))
    warns = [p["text"] for p in probs if p["level"] == "warn" and p.get("signer") is None]
    notes = [n.strip() for n in state.get("summary_notes") or [] if n.strip()]
    if warns or notes:
        lines += ["", *[f"ℹ️ {w}" for w in [*warns, *notes]]]
    blocks = blocking(probs)
    lines.append("")
    if blocks:
        lines.append("Antes de enviar, preciso resolver:")
        lines += [f"  • {p['text']}" for p in blocks]
    else:
        lines.append("Posso enviar? (ou me diga o que mudar)")
    return "\n".join(lines), h, probs


def build_args(state: dict, settings: Settings, file_url: str) -> dict:
    signers_out = []
    for _, s in _ordered(state["signers"]):
        auth = s["auth"]
        item: dict = {
            "name": s["name"].strip(),
            "requirements": [
                {"action": "agree", "role": s["role"]},
                {"action": "provide_evidence", "auth": auth},
            ],
        }
        if s.get("email"):
            item["email"] = s["email"].strip()
        phone = re.sub(r"\D", "", s.get("phone") or "")
        if phone:
            item["phone_number"] = phone
        if settings.send_group:
            item["group"] = s.get("group") or 1
        if settings.silent_send:
            # modo de teste: cria o envelope de verdade, mas a Clicksign não notifica ninguém
            item["communicate_events"] = {"signature_request": "none"}
        signers_out.append(item)
    args: dict = {
        "envelope": {"name": state["envelope_name"].strip()},
        "document": {"file_url": file_url, "filename": state["document"]["filename"]},
        "signers": signers_out,
    }
    if (state.get("message") or "").strip():
        args["notifications"] = {"message": state["message"].strip()}
    schema = json.loads((SCHEMAS_DIR / "dispatch-args.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(args, schema)
    return args
