import type { Plugin } from "@opencode-ai/plugin"
import { fileURLToPath } from "node:url"

// This adapter is intentionally small. Keep policy in hooks/*.sh so it can
// also be used by Claude Code and Codex adapters.
export const HarnessHooks: Plugin = async ({ $ }) => {
  const hook = fileURLToPath(new URL("../../../hooks/protect-secrets.sh", import.meta.url))

  return {
    "tool.execute.before": async (input, output) => {
      if (input.tool !== "read" && input.tool !== "bash") return

      const payload = JSON.stringify({ tool: input.tool, args: output.args })
      await $`printf '%s' ${payload} | bash ${hook}`
    },
  }
}
