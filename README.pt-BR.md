<p><small>🇺🇸 <a href="README.md">English version</a></small></p>

<p align="center">
  <img src="./.github/assets/banner.svg" width="420" alt="ai-harness">
</p>

<h3 align="center">Seus agents, skills, hooks, commands e rules em um só lugar</h3>

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

O `ai-harness` é uma coleção pública e pequena de configurações reutilizáveis para agentes. As partes portáveis usam padrões abertos. A integração específica de cada ferramenta fica nos adapters.

A ideia é simples: escrever uma vez e usar o mesmo trabalho no OpenCode, Claude Code, Codex, Hermes e outras ferramentas.

## Instalação

```bash
git clone https://github.com/Bruno-Furtado/ai-harness.git
cd ai-harness
./sync.sh --dry-run
./sync.sh
```

O `sync.sh` cria symlinks deste repositório para o diretório de configuração de cada ferramenta suportada. Ele nunca substitui um arquivo real existente, e o `--dry-run` mostra todas as mudanças antes de aplicar qualquer coisa. Use `./sync.sh --check` para auditar os links e `./sync.sh --unlink` para remover apenas os links que apontam para cá.

## Suporte às ferramentas

| Ferramenta | Skills | Agents | Commands | Rules | Hooks |
| --- | :---: | :---: | :---: | :---: | :---: |
| OpenCode | Sim | Sim | Sim | Sim | Adapter |
| Claude Code | Sim | Sim | Sim | Sim | Sim |
| Codex | Sim | Parcial | Parcial | Sim | Sim |
| Hermes | Sim | Não | Não | Sim | Não |
| Outras | Agent Skills | Depende | Depende | `AGENTS.md` | Depende |

## Conteúdo

| Caminho | Finalidade |
| --- | --- |
| `agents/` | Exemplos de reviewer somente leitura e validador entre modelos |
| `skills/` | Skills instaláveis no padrão agentskills.io |
| `commands/` | Prompts reutilizáveis para comandos |
| `hooks/` | Hooks pequenos de segurança compartilhados pelos adapters |
| `rules/` | Regras pessoais globais |
| `adapters/` | Exemplos de integração por ferramenta |
| `docs/authoring.md` | Como criar uma skill, agent, command, hook ou rule |
| `docs/templates/` | Templates com critérios de aceite e validação |
| `sync.sh` | Configuração segura e idempotente por symlink |

## Criando um artefato

Leia [docs/authoring.md](docs/authoring.md). O guia cobre onde cada artefato fica, quais campos de frontmatter são portáveis, quais pertencem a uma ferramenta só e como validar o resultado antes de commitar.

## Regras de trabalho

- Cada artefato deve ter uma finalidade clara.
- Declare as premissas antes de agir.
- Defina os critérios de aceite antes da implementação.
- Valide o resultado antes de informar que terminou.
- Use um segundo modelo em planos e mudanças importantes.
- Nunca versione credenciais, dados privados ou tokens.
- Prefira a menor mudança que resolve o problema.

## Segurança

O repositório é público. Não adicione secrets ou contexto privado de projetos. A CI verifica secrets vazados e problemas nos scripts shell. Leia [SECURITY.md](SECURITY.md) antes de adicionar hooks ou integrações.

## Contribuição

Leia [CONTRIBUTING.md](CONTRIBUTING.md). Mudanças passam por pull requests. A branch `main` é protegida.

## Licença

Este projeto está licenciado sob a **MIT License**. Veja o arquivo [`LICENSE`](LICENSE) para mais detalhes.

---

<p align="center">Made with ❤️ in Curitiba 🌳 ☔️</p>
