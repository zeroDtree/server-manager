---
name: security-review
description: 'AI-powered codebase security scanner that reasons about code like a security researcher — tracing data flows, understanding component interactions, and catching vulnerabilities that pattern-matching tools miss. Use this skill when asked to scan code for security vulnerabilities, find bugs, check for SQL injection, XSS, command injection, exposed API keys, hardcoded secrets, insecure dependencies, access control issues, or any request like "is my code secure?", "review for security issues", "audit this codebase", or "check for vulnerabilities". Covers injection flaws, authentication and access control bugs, secrets exposure, weak cryptography, insecure dependencies, and business logic issues across JavaScript, TypeScript, Python, Java, PHP, Go, Ruby, and Rust.'
disable-model-invocation: true
---

# Security Review

Full-repo or path-scoped security audit. Reason about code like a security researcher — trace data flows, verify findings, and report with severity ratings. Patches are proposals only; never auto-apply.

## When to apply

- User asks for a security audit, vulnerability scan, or "is my code secure?"
- User names a path to scan (e.g. "scan `src/auth/` for vulnerabilities")
- User invokes `@security-review` or selects this skill explicitly

This skill audits **codebase or directory scope** — not git diffs or PR-only review.

## How this skill works

1. **Reads code in context** — intent, data flow, framework protections
2. **Traces across files** — user input from entry points to dangerous sinks
3. **Self-verifies findings** — filters false positives before reporting
4. **Assigns severity** — CRITICAL / HIGH / MEDIUM / LOW / INFO
5. **Proposes patches** — concrete before/after for CRITICAL and HIGH only
6. **Requires human approval** — nothing is auto-applied

## Cursor tools

Read reference files on demand — do not inline their content into the report.

| Step | Tools |
|------|-------|
| Scope | `Glob`, `Read` (manifests: `package.json`, `pyproject.toml`, `go.mod`, etc.) |
| Dependency audit | `Shell` — run stack-appropriate audit commands (see Step 2) |
| Secrets scan | `Grep` using patterns from `references/secret-patterns.md`; include CI, Docker, IaC |
| Vuln deep scan | `Grep`, `Read`, `SemanticSearch` (e.g. "where does user input reach SQL/exec/HTML sink") |
| Cross-file flow | `SemanticSearch` + targeted `Read` across entry points → sinks |
| Large repos | Optional parallel `Task` with `subagent_type: explore`, `readonly: true` for scoped sweeps |

## Execution workflow

Follow these steps **in order**. Copy and track:

```
Progress:
- [ ] Step 1: Scope and stack detection
- [ ] Step 2: Dependency audit
- [ ] Step 3: Secrets scan
- [ ] Step 4: Vulnerability deep scan
- [ ] Step 5: Cross-file data flow
- [ ] Step 6: Self-verification
- [ ] Step 7: Security report
- [ ] Step 8: Patch proposals (CRITICAL/HIGH only)
```

### Step 1 — Scope resolution

Determine what to scan:

- If the user named a path (e.g. `src/auth/`), scan only that scope
- If no path given, scan the **entire project** from the workspace root
- Identify language(s) and framework(s) via manifests (`package.json`, `requirements.txt`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `pom.xml`, `build.gradle`, `Gemfile`, `composer.json`, etc.)
- Read `references/language-patterns.md` for framework-specific patterns

### Step 2 — Dependency audit

Run before source-code scanning. Use commands that match the detected stack:

```bash
# Node — use the lockfile-appropriate tool
npm audit --json 2>/dev/null || true
pnpm audit --json 2>/dev/null || true

# Python
uv run pip-audit 2>/dev/null || pip-audit 2>/dev/null || true

# Rust / Go
cargo audit 2>/dev/null || true
govulncheck ./... 2>/dev/null || true
```

Also inspect lockfiles/manifests manually:

- **Node.js**: `package.json`, `package-lock.json` / `pnpm-lock.yaml`
- **Python**: `requirements.txt`, `pyproject.toml`, `Pipfile`
- **Java**: `pom.xml`, `build.gradle`
- **Ruby**: `Gemfile.lock`
- **Rust**: `Cargo.toml`, `Cargo.lock`
- **Go**: `go.sum`

If audit tools are missing or fail, note that in the report and fall back to `references/vulnerable-packages.md`.

### Step 3 — Secrets and exposure scan

Use `Grep` across scope (config, env, CI/CD, Dockerfiles, IaC):

- Hardcoded API keys, tokens, passwords, private keys
- Committed `.env` files
- Secrets in comments or debug logs
- Cloud credentials (AWS, GCP, Azure, Stripe, Twilio, etc.)
- Database connection strings with embedded credentials

Read `references/secret-patterns.md` for regex patterns and entropy heuristics.

### Step 4 — Vulnerability deep scan

Reason about code — do not only pattern-match. Read `references/vuln-categories.md` for full guidance.

**Injection flaws**
- SQL injection: raw queries with interpolation, ORM misuse, second-order SQLi
- XSS: unescaped output, `dangerouslySetInnerHTML`, `innerHTML`, template injection
- Command injection: `exec`/`spawn`/`system` with user input
- LDAP, XPath, header, log injection

**Authentication and access control**
- Missing auth on sensitive endpoints
- BOLA/IDOR
- JWT weaknesses (`alg:none`, weak secrets, missing expiry)
- Session fixation, missing CSRF
- Privilege escalation, mass assignment

**Data handling**
- Sensitive data in logs, errors, or API responses
- Missing encryption at rest or in transit
- Insecure deserialization
- Path traversal, XXE, SSRF

**Cryptography**
- MD5, SHA1, DES for security purposes
- Hardcoded IVs or salts
- `Math.random()` for tokens
- Missing TLS certificate validation

**Business logic**
- Race conditions (TOCTOU)
- Integer overflow in financial code
- Missing rate limiting on sensitive endpoints
- Predictable resource identifiers

### Step 5 — Cross-file data flow

After per-file scan:

- Trace user-controlled input from entry points (HTTP params, headers, body, uploads) to sinks (DB, exec, HTML, file writes)
- Find issues visible only across multiple files
- Check insecure trust boundaries between services or modules

### Step 6 — Self-verification

For each finding:

1. Re-read the relevant code
2. Ask: exploitable as-is, or sanitization upstream?
3. Check framework/middleware mitigations
4. Downgrade or discard false positives
5. Assign final severity and confidence (High / Medium / Low)

### Step 7 — Security report

Output using `references/report-format.md`. Always lead with the findings summary table.

### Step 8 — Patch proposals

For every CRITICAL and HIGH finding:

- Show vulnerable code (before) and fixed code (after)
- Explain what changed and why
- Match existing code style; add a brief inline comment on the fix

State explicitly: **"Review each patch before applying. Nothing has been changed yet."**

Do **not** edit files or apply patches unless the user asks.

## Severity guide

| Severity | Meaning | Example |
|----------|---------|---------|
| CRITICAL | Immediate exploitation risk | SQLi, RCE, auth bypass |
| HIGH | Serious vulnerability, exploit path exists | XSS, IDOR, hardcoded secrets |
| MEDIUM | Exploitable with conditions or chaining | CSRF, open redirect, weak crypto |
| LOW | Best-practice violation, low direct risk | Verbose errors, missing headers |
| INFO | Observation, not a vulnerability | Outdated dependency (no CVE) |

## Output rules

- **Always** produce a findings summary table first (counts by severity)
- **Never** auto-apply patches or edit files — present patches for human review only
- **Always** include confidence per finding (High / Medium / Low)
- **Group findings** by category, not by file
- **Be specific** — file path, line number, vulnerable snippet
- **Explain risk** in plain English — what could an attacker do?
- If clean: state "No vulnerabilities found" and list what was scanned

## Reference files

Load as needed (one level deep from this skill directory):

- `references/vuln-categories.md` — detection signals, safe patterns, escalation checkers
- `references/secret-patterns.md` — regex patterns, entropy heuristics, CI/CD secret risks
- `references/language-patterns.md` — framework-specific patterns (Express, Django, Spring, etc.)
- `references/vulnerable-packages.md` — curated CVE watchlist when audit tools are unavailable
- `references/report-format.md` — report template, finding cards, patch proposal format
