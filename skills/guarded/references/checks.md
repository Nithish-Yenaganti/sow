# Every check, in plain words

| Rule | Severity | Who fixes | What it looks for |
|---|---|---|---|
| `aitools.auto_approve` | high | skill | Committed AI tool settings that let the agent run commands without asking (Copilot auto-approve, Claude Code `bypassPermissions` or a bare `Bash` rule, Gemini YOLO, Codex `approval_policy = "never"`). |
| `aitools.mcp_suspicious` | high | skill | An MCP server in `.mcp.json`, `.cursor/mcp.json`, `.vscode/mcp.json` and similar that downloads or runs code (`curl … \| sh`, `bash -c`, base64, `node -e`). |
| `aitools.mcp_unpinned` | low | you | An MCP server started with `npx`/`uvx` and no fixed version. |
| `aitools.autorun` | medium | you | Hooks (`.claude/settings.json`, `.cursor/hooks.json`) and VS Code tasks that run when the folder opens. High if the command looks risky. |
| `aitools.hidden_text` | high | skill | Invisible Unicode "tag" characters (decoded and shown), text-direction characters in code (Trojan Source), and zero-width characters in instruction files. |
| `aitools.hidden_instructions` | medium | skill | HTML comments or hidden blocks in markdown and agent instruction files that talk to AI tools ("ignore previous instructions", "AI agents must…", `curl … \| sh`). |
| `aitools.tool_poisoning` | high | skill | Tool descriptions or tool results in code that give the model orders (`<IMPORTANT>` blocks, "ignore previous instructions", "don't tell the user"). |
| `secrets.hardcoded` | high | skill + you (rotate) | OpenAI, Anthropic, Stripe live, AWS, GitHub, Slack, Hugging Face, Groq, Replicate and Google keys, private keys, and Supabase `service_role` keys in code. |
| `secrets.env_tracked` | high | skill + you (rotate) | `.env` files committed to git. |
| `secrets.public_env` | high | skill | Server secrets in variables with a browser prefix (`NEXT_PUBLIC_`, `VITE_`, `REACT_APP_`, `EXPO_PUBLIC_`, `PUBLIC_`). |
| `secrets.weak_hash` | medium | skill | Passwords hashed with MD5 or SHA. |
| `data.rls_off` | high | skill | Supabase tables in `public` created in migrations without `enable row level security`. |
| `data.policy_open` | high | skill | Supabase policies that let anyone insert, update or delete (`with check (true)`). |
| `data.firebase_open` | high | skill | Firestore, Storage or Realtime Database rules with `if true` or the default "test mode" date. |
| `data.route_no_auth` | medium | skill | Next.js / SvelteKit API routes that write to the database and show no sign of an auth check. |
| `inject.shell` | high | skill | `exec`/`execSync`/`promisify(exec)`, `spawn(…, {shell: true})`, `subprocess(…, shell=True)`, `os.system` with a command that isn't a fixed string. |
| `inject.eval` | high | skill | `eval`, `new Function`, `vm.run*`, Python `eval`/`exec` on changing text. |
| `inject.sql` | high | skill | SQL text with values pasted in (template literals, f-strings, `+`, `%`, `.format`) passed to a query call, and `$queryRawUnsafe`/`sql.raw` with changing text. |
| `inject.llm_sql` | high | skill | Text-to-SQL chains and agents (LangChain SQL, LlamaIndex NL-SQL, GraphCypherQAChain, PandasAI) or a model's reply passed straight to a query. |
| `inject.llm_exec` | high | skill | Agents that can run code (Python REPL tools, `allow_dangerous_code=True`) or a model's reply passed to `eval`/`exec`/a shell. |
| `ai.injection_risk` | medium | you | An AI feature that reads content you don't control (web pages, documents, RAG results, emails, GitHub issues, or tool input for MCP servers) and can call tools. High for MCP servers. |
| `ai.markdown_images` | medium | skill | AI replies rendered as markdown with images allowed from any address (a known way to send data out). |
| `ai.browser_key` | high | skill | AI SDKs called from the browser (`dangerouslyAllowBrowser: true`). |
| `xss.raw_html` | medium | skill | `dangerouslySetInnerHTML`, `innerHTML`, `insertAdjacentHTML`, `document.write`, `v-html`, `{@html}`, Angular `bypassSecurityTrust*`, Jinja `\|safe`, `mark_safe` with changing values and no sanitizer. |
| `xss.markdown_html` | medium | skill | Markdown with raw HTML on (`rehype-raw` without `rehype-sanitize`, markdown-it `html: true`, `marked` into innerHTML). |
| `xss.no_csp` | low | skill | No Content-Security-Policy anywhere (medium when AI replies are shown as markdown). |
| `server.ssrf` | medium | skill | `fetch`/`axios`/`requests` with a URL that comes from the request or tool input. |
| `server.path` | medium | skill | File reads and writes (`readFile`, `sendFile`, `open`, `send_file`) with a name from the request and no check that it stays in the folder. |
| `server.redirect` | low | skill | Redirects to an address from the request. |
| `server.deserialize` | medium | skill | `pickle`/`joblib`/`dill` loads, `torch.load` without `weights_only=True`, Python `yaml.load` without a safe loader, `numpy.load(allow_pickle=True)`, LangChain `loads`, PHP `unserialize`. |
| `server.cors` | medium | skill | CORS that allows any origin and sends credentials. |
| `server.model_exposed` | medium | you | Ollama or LM Studio ports published to all interfaces in Docker files, or `OLLAMA_HOST=0.0.0.0`. |
| `pkg.lookalike` | medium | you | A dependency one letter off a popular package (`lodahs` vs `lodash`). Offline. |
| `pkg.not_found` | high | skill | A dependency that doesn't exist on npm or PyPI: a made-up name someone could register. Online. |
| `pkg.suspicious` | medium | you | A dependency first published less than 30 days ago, or with almost no downloads. Online. |
| `pkg.vulnerable` | high | skill | A dependency version with a published vulnerability or malware report in OSV (CVE and GHSA ids, with the version that fixes it). Online. Needs a lock file or pinned versions. |

## limits

- It reads code. It can't see your hosting settings, database dashboard, environment variables or anything running live.
- It matches risky patterns, so it can miss a bug written in an unusual way and can flag code that's actually safe. Every finding says why it was flagged.
- It follows values only a short way (the same file, about 25 lines). A request value passed through several functions or files may be missed.
- Prompt injection can't be ruled out by any code check. It only flags the setups where it would do the most damage.
- Known vulnerabilities need exact versions, from `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `uv.lock`, `poetry.lock`, `Pipfile.lock` or `==` pins.
- Languages: JavaScript/TypeScript (incl. Vue, Svelte, Astro) and Python in depth; PHP, Ruby and Go only for SQL and secrets.
- It is not a penetration test, and a clean report doesn't mean an app is secure.
