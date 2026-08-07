<p><small>🇺🇸 <a href="README.md">English version</a></small></p>

<p align="center">
  <img src="./.github/assets/banner.svg" alt="ai-harness">
</p>

<h3 align="center">Escreva um agent, uma skill, um command, um hook ou uma rule uma vez.<br>Um comando instala em todas as ferramentas de IA que você usa.</h3>

<p align="center">
  <a href="https://github.com/Bruno-Furtado/ai-harness/actions/workflows/ci.yml"><img src="https://github.com/Bruno-Furtado/ai-harness/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/ai-harness-cli/"><img src="https://img.shields.io/pypi/v/ai-harness-cli?color=3B82F6&style=flat" alt="PyPI"></a>
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

Escreva um agent, uma skill, um command, um hook ou uma rule uma vez e use em todas as suas ferramentas. A parte portável segue padrões abertos, Agent Skills e `AGENTS.md`, e a integração que cada ferramenta exige fica em `adapters/`, então nada aqui depende de um fornecedor específico.

## Instalação

O `harness` pergunta em quais ferramentas instalar e quais artefatos levar, e coloca cada um onde a ferramenta procura.

```bash
pip install ai-harness-cli
harness
```

Para escrever os seus próprios artefatos, clone este repositório e rode `./harness` de dentro dele. O clone cria links em vez de copiar, então um `git pull` chega em todas as ferramentas de uma vez.

```bash
harness update   # traz os artefatos novos e reconcilia
harness check    # audita o que está instalado
harness remove   # remove apenas o que o harness instalou
```

## Conteúdo

O mapa do repositório, para escrever um artefato ou achar onde cada peça mora.

| Caminho | O que fica ali |
| --- | --- |
| `agents/` | Agents, no formato que cada ferramenta lê |
| `skills/` | Skills no layout aberto do Agent Skills |
| `commands/` | Prompts que cada ferramenta expõe como comando |
| `hooks/` | Scripts de guarda compartilhados pelos adapters |
| `rules/` | Regras globais, linkadas como `AGENTS.md` |
| `adapters/` | O que cada ferramenta precisa para integrar o resto |
| `docs/` | Como criar um artefato e como as peças se encaixam |
| `harness`, `ai_harness/` | O instalador |
| `targets.json` | Onde cada artefato é instalado, por ferramenta |
| `CONTRIBUTING.md` | Como propor uma mudança e como as releases são publicadas |

## Catálogo

O que você ganha depois de instalar.

<!-- catalog:start -->

### Skills

| Nome | O que faz |
| --- | --- |
| [dream](skills/dream/SKILL.md) | Lê as sessões do dia e sugere o que vale lembrar, por exemplo que você prefere Postgres a MySQL. |
| [news-digest](skills/news-digest/SKILL.md) | Lê seus feeds e entrega as notícias do dia numa mensagem curta, pulando o que você já viu. |
| [task-delegation](skills/task-delegation/SKILL.md) | Passa uma tarefa pesada para o OpenCode rodar no modelo mais forte que você tem. |
| [topic-research](skills/topic-research/SKILL.md) | Pesquisa um tema no Hacker News, Reddit e GitHub, com um link atrás de cada afirmação. |

### Agents

| Nome | O que faz |
| --- | --- |
| [code-reviewer](agents/code-reviewer.md) | Lê o seu diff e aponta bug, risco de segurança e teste faltando. Não altera nada. |
| [news-digest-validator](agents/news-digest-validator.md) | Confere o digest antes de chegar em você e corta notícia repetida, óbvia ou mal traduzida. |
| [proposal-validator](agents/proposal-validator.md) | Manda o seu plano para outro modelo, para pegar o que o primeiro deixou passar. |

### Commands

| Nome | O que faz |
| --- | --- |
| [dream](commands/dream.md) | Roda o dream e aplica as sugestões que você aprovar, uma a uma. |
| [news-digest](commands/news-digest.md) | Pede o digest de hoje agora. |
| [review-changes](commands/review-changes.md) | Revisa o que você mudou, antes de abrir o pull request. |
| [topic-research](commands/topic-research.md) | Pesquisa um tema e escreve um relatório conferível, porque toda afirmação cita a fonte. |
| [validate-proposal](commands/validate-proposal.md) | Manda o plano que está na mesa para uma segunda opinião independente. |

### Hooks

| Nome | O que faz |
| --- | --- |
| [protect-secrets](hooks/protect-secrets.sh) | Impede o agente de abrir .env, chave e certificado, mesmo que você peça sem querer. |

### Rules

| Nome | O que faz |
| --- | --- |
| [global](rules/global.md) | Diz ao agente como trabalhar em todo projeto: perguntar na dúvida, mostrar evidência antes de dizer que terminou. |

<!-- catalog:end -->

## Integração

É assim que cada artefato é instalado.

<!-- integration:start -->

| Artefato | Claude Code | OpenCode | Codex | Hermes |
| --- | --- | --- | --- | --- |
| `skills/<name>/` | `~/.claude/skills` | `~/.config/opencode/skills` | `~/.agents/skills` | `~/.hermes/skills` |
| `agents/<name>.md` | `~/.claude/agents` | `~/.config/opencode/agents` | Não suportado | Não suportado |
| `commands/<name>.md` | `~/.claude/commands` | `~/.config/opencode/commands` | `~/.codex/prompts` | Não suportado |
| `rules/global.md` | `~/.claude/CLAUDE.md` | `~/.config/opencode/AGENTS.md` | `~/.codex/AGENTS.md` | Não suportado |

<!-- integration:end -->

## Suporte às ferramentas

| Ferramenta | Skills | Agents | Commands | Rules | Hooks |
| --- | :---: | :---: | :---: | :---: | :---: |
| OpenCode | Sim | Sim | Sim | Sim | Adapter |
| Claude Code | Sim | Sim | Sim | Sim | Sim |
| Codex | Sim | Parcial | Parcial | Sim | Sim |
| Hermes | Sim | Não | Não | Workspace | Não |

Parcial quer dizer que o Codex não tem formato de subagent, e os prompts dele não documentam frontmatter, então só o corpo é aproveitado. Workspace quer dizer que o Hermes lê as regras do projeto, então não há arquivo global para instalar.

## Regras de trabalho

- Uma finalidade por artefato. `name` e `description` continuam portáveis, e qualquer restrição também é declarada no corpo.
- Critérios de aceite antes da implementação, evidência antes de dizer que terminou.
- Sem credenciais, sem modelo fixo, sem caminho de máquina.

O motivo de cada uma está em [docs/authoring.md](docs/authoring.md).

---

<sub>Qualquer outra ferramenta que leia Agent Skills e `AGENTS.md` pega as skills e as rules sozinha. Basta apontar para `skills/` e para `rules/global.md`. O resto depende do que essa ferramenta suporta.</sub>

<p align="center">Made with ❤️ in Curitiba 🌳 ☔️</p>
