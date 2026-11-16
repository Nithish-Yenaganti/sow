# Sources

Every rule cites one or more of these ids. CVE entries are real incidents that show the pattern happens in practice; check NVD for the current details.

## Standards

| id | Source |
|---|---|
| owasp-llm01 | [OWASP Top 10 for LLM Applications 2025: LLM01 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) |
| owasp-llm02 | [OWASP LLM02: Sensitive Information Disclosure](https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/) |
| owasp-llm03 | [OWASP LLM03: Supply Chain](https://genai.owasp.org/llmrisk/llm032025-supply-chain/) |
| owasp-llm05 | [OWASP LLM05: Improper Output Handling](https://genai.owasp.org/llmrisk/llm052025-improper-output-handling/) |
| owasp-llm06 | [OWASP LLM06: Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/) |
| owasp-a01 | [OWASP Top 10 A01: Broken Access Control](https://owasp.org/Top10/A01_2021-Broken_Access_Control/) |
| owasp-a02 | [OWASP Top 10 A02: Cryptographic Failures](https://owasp.org/Top10/A02_2021-Cryptographic_Failures/) |
| owasp-a03 | [OWASP Top 10 A03: Injection](https://owasp.org/Top10/A03_2021-Injection/) |
| owasp-a05 | [OWASP Top 10 A05: Security Misconfiguration](https://owasp.org/Top10/A05_2021-Security_Misconfiguration/) |
| owasp-a06 | [OWASP Top 10 A06: Vulnerable and Outdated Components](https://owasp.org/Top10/A06_2021-Vulnerable_and_Outdated_Components/) |
| owasp-a07 | [OWASP Top 10 A07: Identification and Authentication Failures](https://owasp.org/Top10/A07_2021-Identification_and_Authentication_Failures/) |
| owasp-a10 | [OWASP Top 10 A10: Server-Side Request Forgery](https://owasp.org/Top10/A10_2021-Server-Side_Request_Forgery_%28SSRF%29/) |
| owasp-csp | [OWASP Content Security Policy Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html) |
| cwe-22 | [CWE-22 Path Traversal](https://cwe.mitre.org/data/definitions/22.html) |
| cwe-78 | [CWE-78 OS Command Injection](https://cwe.mitre.org/data/definitions/78.html) |
| cwe-79 | [CWE-79 Cross-site Scripting](https://cwe.mitre.org/data/definitions/79.html) |
| cwe-89 | [CWE-89 SQL Injection](https://cwe.mitre.org/data/definitions/89.html) |
| cwe-95 | [CWE-95 Eval Injection](https://cwe.mitre.org/data/definitions/95.html) |
| cwe-200 | [CWE-200 Exposure of Sensitive Information](https://cwe.mitre.org/data/definitions/200.html) |
| cwe-502 | [CWE-502 Deserialization of Untrusted Data](https://cwe.mitre.org/data/definitions/502.html) |
| cwe-538 | [CWE-538 Sensitive Information in Externally-Accessible File](https://cwe.mitre.org/data/definitions/538.html) |
| cwe-601 | [CWE-601 Open Redirect](https://cwe.mitre.org/data/definitions/601.html) |
| cwe-798 | [CWE-798 Hard-coded Credentials](https://cwe.mitre.org/data/definitions/798.html) |
| cwe-862 | [CWE-862 Missing Authorization](https://cwe.mitre.org/data/definitions/862.html) |
| cwe-916 | [CWE-916 Password Hash With Insufficient Effort](https://cwe.mitre.org/data/definitions/916.html) |
| cwe-918 | [CWE-918 Server-Side Request Forgery](https://cwe.mitre.org/data/definitions/918.html) |
| cwe-942 | [CWE-942 Permissive Cross-domain Policy](https://cwe.mitre.org/data/definitions/942.html) |
| supabase-rls | [Supabase: Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security) |
| firebase-rules | [Firebase: Fix insecure rules](https://firebase.google.com/docs/rules/insecure-rules) |
| osv | [OSV: open source vulnerability database](https://osv.dev) |
| trojan-source | [Trojan Source: invisible vulnerabilities (Boucher & Anderson)](https://trojansource.codes/) |
| p2sql | [Pedro et al., "Prompt-to-SQL injections in LLM-integrated web applications", ICSE 2025](https://syssec.dpss.inesc-id.pt/papers/pedro_icse25.pdf) |
| slopsquatting | [Spracklen et al., "We Have a Package for You!" (package hallucinations), USENIX Security 2025](https://arxiv.org/abs/2406.10279) |
| typosquatting | [OWASP CI/CD Security Risks: CICD-SEC-3 Dependency Chain Abuse (typosquatting)](https://owasp.org/www-project-top-10-ci-cd-security-risks/CICD-SEC-03-Dependency-Chain-Abuse) |
| lethal-trifecta | [Simon Willison: the lethal trifecta for AI agents](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/) |
| mcp-tool-poisoning | [Invariant Labs: MCP security notification, tool poisoning attacks](https://invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks) |
| gitlab-duo | [Simon Willison: remote prompt injection in GitLab Duo (data sent out through image links)](https://simonwillison.net/2025/May/23/remote-prompt-injection-in-gitlab-duo/) |

## Real incidents (CVEs)

| id | What happened |
|---|---|
| CVE-2025-53773 | GitHub Copilot: instructions hidden in a README made the agent turn on auto-approve in `.vscode/settings.json`, then run commands. |
| CVE-2025-54135 | Cursor "CurXecute": a message the agent summarized made it write `.cursor/mcp.json`, which ran the attacker's command. |
| CVE-2025-54136 | Cursor "MCPoison": an MCP config approved once was changed later and kept running without a new prompt. |
| CVE-2025-59536 | Claude Code: a hook in project settings ran before the trust prompt. |
| CVE-2025-65099 | Claude Code: a project config ran code before the trust prompt. |
| CVE-2025-59145 | GitHub Copilot "CamoLeak": hidden comments in pull requests made Copilot leak private code. |
| CVE-2025-53107 | git-mcp-server: git commands built from tool input and run through a shell. Fixed in 2.1.5. |
| CVE-2025-53967 | figma-developer-mcp: a URL from tool input pasted into a `curl` command run through a shell. Fixed in 0.6.3. |
| CVE-2025-53818 | github-kanban-mcp-server: tool input pasted into `gh` commands run through a shell. |
| CVE-2025-6514 | mcp-remote: a value from a remote server ended up in a local command. Fixed in 0.1.16. |
| CVE-2024-12366 | PandasAI: prompt injection led to code execution. |
| CVE-2024-8309 | LangChain GraphCypherQAChain: AI-written database queries ran without checks. |
| CVE-2024-12911 | LlamaIndex JSONalyzeQueryEngine: AI-written SQL ran directly. |
| CVE-2025-1793 | LlamaIndex vector store integrations: SQL built from strings. |
| CVE-2025-68664 | LangChain "LangGrinch": crafted metadata loaded as objects could pull out secrets. |
| CVE-2025-48757 | Lovable: about 170 apps shipped Supabase tables anyone could read or write (missing RLS). |
| CVE-2026-41318 | AnythingLLM: text from the model rendered as HTML, giving stored XSS. |
| CVE-2024-37032 | Ollama "Probllama": path traversal that could lead to code execution on exposed servers. |
| CVE-2026-7482 | Ollama "Bleeding Llama": a crafted model file leaked server memory on exposed servers. |
