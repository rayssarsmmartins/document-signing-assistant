"""Contratos dos arquivos do workspace que não são código (skills, regras, orquestração)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = sorted((ROOT / ".agents" / "skills").glob("*/SKILL.md"))


def _frontmatter(p: Path) -> str:
    return p.read_text(encoding="utf-8").split("---")[1]


def test_skills_have_valid_frontmatter():
    assert SKILLS, "nenhuma skill encontrada"
    for p in SKILLS:
        fm = _frontmatter(p)
        name = re.search(r"^name: (.+)$", fm, re.M).group(1).strip()
        desc = re.search(r"^description: (.+)$", fm, re.M).group(1).strip()
        cat = re.search(r"^  category: (.+)$", fm, re.M).group(1).strip()
        assert name == p.parent.name, p
        assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name), p
        assert name.startswith(cat + "-"), p
        assert cat in {"sign", "track", "write", "ops"}, p
        assert len(desc) <= 1024, p


def test_acknowledge_first_is_wired():
    conv = (ROOT / ".agents/rules/conversation.md").read_text(encoding="utf-8")
    assert "Acknowledge first, then work" in conv
    assert "before any tool call" in conv
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "Acknowledge first" in agents
    orch = (ROOT / ".agents/commands/send-for-signature.md").read_text(encoding="utf-8")
    # intake, resposta do usuário e envio têm ponto de confirmação explícito
    assert orch.count("**Ack") >= 3


def test_no_contradicting_silence_instruction():
    for p in [ROOT / "AGENTS.md", *ROOT.glob(".agents/**/*.md")]:
        text = p.read_text(encoding="utf-8")
        assert "Don't narrate the process" not in text, p
        assert "silent reading" not in text, p


def test_e13_does_not_filter_by_exact_name():
    d = (ROOT / ".agents/skills/sign-dispatch/SKILL.md").read_text(encoding="utf-8")
    assert "Don't filter by `name`" in d
    assert "Never call create again" in d


def test_howto_and_capabilities_stay_in_sync():
    howto = (ROOT / "docs/howto-conversas.md").read_text(encoding="utf-8")
    caps = (ROOT / ".agents/knowledge/capabilities.md").read_text(encoding="utf-8")
    # mesmas fronteiras nos dois lados: o que é planejado/bloqueado não pode aparecer como pronto
    pairs = [
        ("Receber o documento assinado 🔜", "Get the signed PDF back in the chat | planned"),
        ("Enviar a partir de um modelo da conta 🔜", "Send from an account template (\"modelo\") | planned"),
        ("Falar por áudio 🧪", "Voice message (`voice-*.ogg`) | experimental"),
        ("Cancelar ou editar um envio já feito", "Cancel / edit a sent envelope | blocked"),
        ("Definir prazo para assinar", "Set a deadline / read the deadline | blocked"),
    ]
    for user_side, agent_side in pairs:
        assert user_side in howto, user_side
        assert agent_side in caps, agent_side


def test_voice_never_counts_as_consent_when_unclear():
    conv = (ROOT / ".agents/rules/conversation.md").read_text(encoding="utf-8")
    assert "Never** read a garbled" in conv
    assert "confirm in text first" in conv
