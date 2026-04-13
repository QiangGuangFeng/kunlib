# 🧬 KunLib — Genetic Breeding Analysis Skill Library

KunLib is a skill library for genetic breeding analysis tasks.
Each skill is a self-contained module with standardized input/output,
discoverable by AI agents (kunbreed, OpenClaw, etc.) via `SKILL.md`.

## Quick Start

```bash
pip install -e .
kunlib list
kunlib run <skill> --demo --output /tmp/out
```

## Direct Execution

Every skill script is independently runnable:

```bash
python skills/hiblup-ebv/hiblup_ebv.py --demo --output /tmp/out
```

## For AI Agents

```python
from kunlib.agent_adapter import KunLibAdapter

adapter = KunLibAdapter()
docs = adapter.get_skill_docs()       # Read SKILL.md for methodology
manifest = adapter.get_skill_manifest()  # Structured skill catalog
result = adapter.run_skill("hiblup-ebv", {"demo": True, "output": "/tmp/out"})
```

## Add a Skill

See [AGENTS.md](AGENTS.md) §"Converting a User Script into a KunLib Skill".

## License

MIT