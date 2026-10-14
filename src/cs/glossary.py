"""Vocabulário da persona ↔ vocabulário da API.

A conversa usa só a coluna da esquerda (pt-BR); o payload usa só a da direita.
Derivado do guia de signatários do MCP da Clicksign (glossário PT→EN de papéis).
"""

from __future__ import annotations

import unicodedata

# canonical role -> rótulo pt-BR exibido no resumo
ROLE_LABELS: dict[str, str] = {
    "sign": "assina",
    "party": "parte",
    "witness": "testemunha",
    "approve": "aprova",
    "buyer": "comprador(a)",
    "seller": "vendedor(a)",
    "contractor": "contratante",
    "contractee": "contratado(a)",
    "lessor": "locador(a)",
    "lessee": "locatário(a)",
    "grantor": "outorgante",
    "grantee": "outorgado(a)",
    "legal_representative": "representante legal",
    "guarantor": "fiador(a)",
    "debtor": "devedor(a)",
    "creditor": "credor(a)",
    "partner": "sócio(a)",
    "director": "diretor(a)",
    "administrator": "administrador(a)",
    "lawyer": "advogado(a)",
    "attorney": "procurador(a)",
    "tenant": "inquilino(a)",
    "owner": "proprietário(a)",
    "employee": "empregado(a)",
    "employer": "empregador(a)",
    "donor": "doador(a)",
    "donee": "donatário(a)",
    "manager": "gerente",
    "president": "presidente",
    "broker": "corretor(a)",
    "service_provider": "prestador(a) de serviço",
    "intervening": "interveniente",
    "franchisor": "franqueador(a)",
    "franchisee": "franqueado(a)",
    "lender": "credor(a)",
    "borrower": "tomador(a)",
    "licensor": "licenciante",
    "licensed": "licenciado(a)",
}

# termos pt-BR (sem acento, minúsculos) -> canonical. Só termos inequívocos.
_PT_TO_ROLE: dict[str, str] = {
    "testemunha": "witness",
    "aprovador": "approve", "aprovadora": "approve",
    "comprador": "buyer", "compradora": "buyer",
    "vendedor": "seller", "vendedora": "seller",
    "contratante": "contractor",
    "contratado": "contractee", "contratada": "contractee",
    "locador": "lessor", "locadora": "lessor",
    "locatario": "lessee", "locataria": "lessee",
    "outorgante": "grantor",
    "outorgado": "grantee", "outorgada": "grantee",
    "representante legal": "legal_representative",
    "fiador": "guarantor", "fiadora": "guarantor",
    "devedor": "debtor", "devedora": "debtor",
    "credor": "creditor", "credora": "creditor",
    "socio": "partner", "socia": "partner",
    "diretor": "director", "diretora": "director",
    "administrador": "administrator", "administradora": "administrator",
    "advogado": "lawyer", "advogada": "lawyer",
    "procurador": "attorney", "procuradora": "attorney",
    "inquilino": "tenant", "inquilina": "tenant",
    "proprietario": "owner", "proprietaria": "owner",
    "funcionario": "employee", "empregado": "employee", "empregada": "employee",
    "empregador": "employer", "empregadora": "employer",
    "doador": "donor", "doadora": "donor",
    "donatario": "donee", "donataria": "donee",
    "gerente": "manager",
    "presidente": "president",
    "corretor": "broker", "corretora": "broker",
    "prestador": "service_provider", "prestadora": "service_provider",
    "interveniente": "intervening",
    "franqueador": "franchisor", "franqueadora": "franchisor",
    "franqueado": "franchisee", "franqueada": "franchisee",
    "assina": "sign", "signatario": "sign", "signataria": "sign",
}

# auth -> como a persona entende
AUTH_LABELS: dict[str, str] = {
    "email": "código por e-mail",
    "sms": "código por SMS",
    "whatsapp": "código por WhatsApp",
    "selfie": "selfie",
    "official_document": "foto de documento oficial",
    "liveness": "prova de vida (vídeo)",
    "address_proof": "comprovante de endereço",
    "icp_brasil": "certificado digital ICP-Brasil",
    "pix": "Pix",
}

# auth -> campo de contato obrigatório
AUTH_CONTACT: dict[str, str] = {"email": "email", "sms": "phone", "whatsapp": "phone"}

DEFAULT_AUTH = "email"
DEFAULT_ROLE = "sign"


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.strip().lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def role_from_pt(term: str) -> str | None:
    """Mapeia um termo pt-BR (ou já canônico) para o role da API; None se ambíguo/desconhecido."""
    t = _norm(term)
    if t in ROLE_LABELS:
        return t
    return _PT_TO_ROLE.get(t)


def role_label(role: str) -> str:
    return ROLE_LABELS.get(role, role)


def auth_label(auth: str) -> str:
    return AUTH_LABELS.get(auth, auth)
