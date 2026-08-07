<p><small>🇺🇸 <a href="README.md">English version</a></small></p>

<p align="center">
  <img src="./.github/assets/banner.svg" alt="ai-harness">
</p>

<h3 align="center">Agents, skills, commands, hooks e rules agnósticos de ferramenta, em um só lugar</h3>

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

## Catálogo

<!-- catalog:start -->

### Skills

| Nome | O que faz |
| --- | --- |
| [dream](skills/dream/SKILL.md) | Revisa as sessões do dia e propõe mudanças de memória, cada item com evidência citada. |
| [news-digest](skills/news-digest/SKILL.md) | Monta um resumo pessoal a partir dos seus próprios feeds, com memória de repetidos e conferência por um segundo modelo. |
| [task-delegation](skills/task-delegation/SKILL.md) | Entrega uma tarefa ao OpenCode, que a executa no melhor modelo disponível para aquele nível. |
| [topic-research](skills/topic-research/SKILL.md) | Coleta o que foi dito sobre um tema em várias fontes e relata com citações. |

### Agents

| Nome | O que faz |
| --- | --- |
| [code-reviewer](agents/code-reviewer.md) | Revisa uma mudança e relata riscos, regressões e testes faltando. Nunca edita arquivos. |
| [news-digest-validator](agents/news-digest-validator.md) | Confere a seleção do digest procurando repetidos, notícias óbvias e traduções fracas antes da entrega. |
| [proposal-validator](agents/proposal-validator.md) | Dá uma segunda opinião sobre um plano, uma mudança ou um relatório, em outro modelo. Somente leitura. |

### Commands

| Nome | O que faz |
| --- | --- |
| [dream](commands/dream.md) | Roda a rotina de memória do dream, ou aplica, lista e descarta as propostas dela. |
| [news-digest](commands/news-digest.md) | Monta o digest de notícias e entrega como uma única mensagem curta. |
| [review-changes](commands/review-changes.md) | Revisa as mudanças atuais do git buscando correção, segurança e testes faltando. |
| [topic-research](commands/topic-research.md) | Pesquisa um tema e escreve um relatório onde toda afirmação cita um item coletado. |
| [validate-proposal](commands/validate-proposal.md) | Envia o plano, a mudança ou o relatório atual para uma segunda opinião independente. |

### Hooks

| Nome | O que faz |
| --- | --- |
| [protect-secrets](hooks/protect-secrets.sh) | Bloqueia chamadas de ferramenta que referenciam arquivos .env, de credencial, segredo, certificado ou chave. |

### Rules

| Nome | O que faz |
| --- | --- |
| [global](rules/global.md) | Regras permanentes para todo projeto: forma de trabalho, validação, segurança e comunicação. |

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
| `harness`, `ai_harness/` | O instalador |
| `targets.json` | Onde cada artefato é instalado, por ferramenta |
| `CONTRIBUTING.md` | Como propor uma mudança e como as releases são publicadas |

## Regras de trabalho

- Uma finalidade por artefato. `name` e `description` continuam portáveis, e qualquer restrição também é declarada no corpo.
- Critérios de aceite antes da implementação, evidência antes de dizer que terminou.
- Sem credenciais, sem modelo fixo, sem caminho de máquina.

O motivo de cada uma está em [docs/authoring.md](docs/authoring.md).

---

<sub>Qualquer outra ferramenta que leia Agent Skills e `AGENTS.md` pega as skills e as rules sozinha. Basta apontar para `skills/` e para `rules/global.md`. O resto depende do que essa ferramenta suporta.</sub>

<p align="center">Made with ❤️ in Curitiba 🌳 ☔️</p>
