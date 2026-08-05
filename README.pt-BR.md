<p><small>🇺🇸 <a href="README.md">English version</a></small></p>

<p align="center">
  <img src="./.github/assets/banner.svg" alt="ai-harness">
</p>

<h3 align="center">Agents, skills, commands, hooks e rules agnósticos de ferramenta, em um só lugar</h3>

<p align="center">
  <a href="https://github.com/Bruno-Furtado/ai-harness/actions/workflows/ci.yml"><img src="https://github.com/Bruno-Furtado/ai-harness/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/licença-MIT-22C55E?style=flat" alt="Licença: MIT"></a>
  <img src="https://img.shields.io/badge/padrão-agentskills.io-3B82F6?style=flat" alt="Agent Skills">
  <img src="https://img.shields.io/badge/padrão-AGENTS.md-3B82F6?style=flat" alt="AGENTS.md">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/ferramenta-OpenCode-111827?style=flat" alt="OpenCode">
  <img src="https://img.shields.io/badge/ferramenta-Claude_Code-D97706?style=flat" alt="Claude Code">
  <img src="https://img.shields.io/badge/ferramenta-Codex-059669?style=flat" alt="Codex">
  <img src="https://img.shields.io/badge/ferramenta-Hermes-7C3AED?style=flat" alt="Hermes">
</p>

## O que é

Escreva um agent, uma skill, um command, um hook ou uma rule uma vez e use em todas as ferramentas que você usa. A parte portável segue padrões abertos, Agent Skills e `AGENTS.md`, e a integração que cada ferramenta exige fica em `adapters/`, então nada aqui depende de um fornecedor específico.

## Instalação

```bash
git clone https://github.com/Bruno-Furtado/ai-harness.git
cd ai-harness

./sync.sh --dry-run   # mostra todas as mudanças, sem escrever nada
./sync.sh             # cria os links dos artefatos em cada ferramenta
./sync.sh --check     # audita os links depois
./sync.sh --unlink    # remove apenas os links que apontam para cá
```

## Suporte às ferramentas

| Ferramenta | Skills | Agents | Commands | Rules | Hooks | Observação |
| --- | :---: | :---: | :---: | :---: | :---: | --- |
| OpenCode | Sim | Sim | Sim | Sim | Adapter | Hooks chegam por plugin |
| Claude Code | Sim | Sim | Sim | Sim | Sim | |
| Codex | Sim | Parcial | Parcial | Sim | Sim | Não tem formato de subagent, e os prompts não documentam frontmatter, então só o corpo é aproveitado |
| Hermes | Sim | Não | Não | Sim | Não | Consome apenas skills e regras de workspace |

Qualquer outra ferramenta que leia Agent Skills e `AGENTS.md` recebe as skills e as rules. O resto depende do que essa ferramenta suporta.

## Conteúdo

| Caminho | O que fica ali |
| --- | --- |
| `agents/` | Agents, no formato que cada ferramenta lê |
| `skills/` | Skills no layout aberto do Agent Skills |
| `commands/` | Prompts que cada ferramenta expõe como comando |
| `hooks/` | Scripts de guarda compartilhados pelos adapters |
| `rules/` | Regras globais, linkadas como `AGENTS.md` |
| `adapters/` | O que cada ferramenta precisa para integrar o resto |
| `docs/` | Como criar um artefato e como as peças se encaixam |
| `CONTRIBUTING.md` | Como propor uma mudança e como as releases são publicadas |
| `sync.sh` | Cria os links de tudo nas ferramentas que você usa |

## Regras de trabalho

- Uma finalidade por artefato. `name` e `description` continuam portáveis, e qualquer restrição também é declarada no corpo.
- Critérios de aceite antes da implementação, evidência antes de dizer que terminou.
- Sem credenciais, sem modelo fixo, sem caminho de máquina.

O motivo de cada uma está em [docs/authoring.md](docs/authoring.md).

---

<p align="center">Made with ❤️ in Curitiba 🌳 ☔️</p>
