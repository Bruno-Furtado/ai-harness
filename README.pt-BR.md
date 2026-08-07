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

Se quiser só as skills, sem clonar:

```bash
npx skills add Bruno-Furtado/ai-harness
```

## Catálogo

Todos os artefatos deste repositório. A tabela é gerada a partir dos próprios arquivos, então não desatualiza.

<!-- catalog:start -->

### Skills

| Nome | O que faz | Como usar |
| --- | --- | --- |
| [dream](skills/dream/SKILL.md) | Revisa as sessões do dia e propõe mudanças de memória, cada item com evidência citada. | `/dream`, depois `/dream apply 1,3` |
| [news-digest](skills/news-digest/SKILL.md) | Monta um resumo pessoal a partir dos seus próprios feeds, com memória de repetidos e conferência por um segundo modelo. | `/news-digest [seções]` |
| [task-delegation](skills/task-delegation/SKILL.md) | Entrega uma tarefa ao OpenCode, que a executa no melhor modelo disponível para aquele nível. | Peça, ou deixe a ferramenta disparar |
| [topic-research](skills/topic-research/SKILL.md) | Coleta o que foi dito sobre um tema em várias fontes e relata com citações. | `/topic-research <tema>` |

### Agents

| Nome | O que faz | Como usar |
| --- | --- | --- |
| [code-reviewer](agents/code-reviewer.md) | Revisa uma mudança e relata riscos, regressões e testes faltando. Nunca edita arquivos. | `/review-changes`, ou delegue pelo nome |
| [news-digest-validator](agents/news-digest-validator.md) | Confere a seleção do digest procurando repetidos, notícias óbvias e traduções fracas antes da entrega. | Chamado pela skill `news-digest` |
| [proposal-validator](agents/proposal-validator.md) | Dá uma segunda opinião sobre um plano, uma mudança ou um relatório, em outro modelo. Somente leitura. | `/validate-proposal`, ou delegue pelo nome |

### Commands

| Nome | O que faz | Como usar |
| --- | --- | --- |
| [dream](commands/dream.md) | Roda a rotina de memória do dream, ou aplica, lista e descarta as propostas dela. | `/dream`, `/dream apply all`, `/dream list` |
| [news-digest](commands/news-digest.md) | Monta o digest de notícias e entrega como uma única mensagem curta. | `/news-digest [seções]` |
| [review-changes](commands/review-changes.md) | Revisa as mudanças atuais do git buscando correção, segurança e testes faltando. | `/review-changes` |
| [topic-research](commands/topic-research.md) | Pesquisa um tema e escreve um relatório onde toda afirmação cita um item coletado. | `/topic-research <tema>` |
| [validate-proposal](commands/validate-proposal.md) | Envia o plano, a mudança ou o relatório atual para uma segunda opinião independente. | `/validate-proposal` |

### Hooks

| Nome | O que faz | Como usar |
| --- | --- | --- |
| [protect-secrets](hooks/protect-secrets.sh) | Bloqueia chamadas de ferramenta que referenciam arquivos .env, de credencial, segredo, certificado ou chave. | Ligado uma vez por ferramenta, veja Integração |

### Rules

| Nome | O que faz | Como usar |
| --- | --- | --- |
| [global](rules/global.md) | Regras permanentes para todo projeto: forma de trabalho, validação, segurança e comunicação. | Linkado como o `AGENTS.md` global |

<!-- catalog:end -->

## Integração

O `sync.sh` cria um symlink por artefato, então uma edição aqui chega em todas as ferramentas de uma vez. É assim que cada um é instalado:

| Artefato | Claude Code | OpenCode | Codex | Hermes |
| --- | --- | --- | --- | --- |
| `skills/<nome>/` | `~/.claude/skills/` | `~/.config/opencode/skills/` | `~/.agents/skills/` | `~/.hermes/skills/` |
| `agents/<nome>.md` | `~/.claude/agents/` | `~/.config/opencode/agents/` | Não suportado | Não suportado |
| `commands/<nome>.md` | `~/.claude/commands/` | `~/.config/opencode/commands/` | `~/.codex/prompts/` | Não suportado |
| `rules/global.md` | `~/.claude/CLAUDE.md` | `~/.config/opencode/AGENTS.md` | `~/.codex/AGENTS.md` | Regras do workspace |

Depois é só chamar pelo nome que está no catálogo: `/news-digest` como comando, `code-reviewer` como subagent, e uma skill pedindo o que ela faz.

Hooks são a exceção, porque hook é código executável e nenhuma ferramenta aceita um só por symlink. A ligação é feita uma vez por ferramenta:

| Ferramenta | Como |
| --- | --- |
| Claude Code | Cole [adapters/claude/settings.snippet.json](adapters/claude/settings.snippet.json) no `~/.claude/settings.json`, trocando o placeholder pelo caminho absoluto deste clone |
| Codex | Igual, usando [adapters/codex/hooks.json](adapters/codex/hooks.json) |
| OpenCode | Já está pronto. O `sync.sh` linka [o plugin](adapters/opencode/plugins/harness-hooks.ts), que chama o mesmo script |

Qualquer outra ferramenta que leia Agent Skills e `AGENTS.md` pega as skills e as rules sozinha. Basta apontar para `skills/` e para `rules/global.md`.

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
