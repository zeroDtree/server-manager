# Security Report Format

Use this template for all security-review skill output. Generated during Step 7.

---

## Report structure

### Header

```markdown
# Security Review Report

**Project:** <project name or path>
**Scan date:** <today's date>
**Scope:** <files/directories scanned>
**Languages detected:** <list>
**Frameworks detected:** <list>
```

---

### Executive summary table

Always show this first:

| Severity | Count |
|----------|-------|
| CRITICAL | <n> |
| HIGH | <n> |
| MEDIUM | <n> |
| LOW | <n> |
| INFO | <n> |
| **Total** | **<n>** |

**Dependency audit:** <n> vulnerable packages found
**Secrets scan:** <n> exposed credentials found

---

### Findings (grouped by category)

For each finding, use this card format:

```markdown
### [SEVERITY] — [Vulnerability type]

**Confidence:** High / Medium / Low

**Location:** `src/routes/users.js`, line 47

**Vulnerable code:**
```js
const query = `SELECT * FROM users WHERE id = ${req.params.id}`;
db.execute(query);
```

**Risk:**
An attacker can manipulate the `id` parameter to execute arbitrary SQL commands,
potentially dumping the database or bypassing authentication.

Example: `GET /users/1 OR 1=1--`

**Recommended fix:**
Use parameterized queries:

```js
const query = 'SELECT * FROM users WHERE id = ?';
db.execute(query, [req.params.id]);
```

**Reference:** OWASP A03:2021 – Injection
```

---

### Dependency audit section

```markdown
## Dependency audit

### HIGH — lodash@4.17.20 (`package.json`)
- **CVE-2021-23337:** Prototype pollution via zipObjectDeep()
- **Fix:** `npm install lodash@4.17.21`

### MEDIUM — axios@0.27.2 (`package.json`)
- **CVE-2023-45857:** CSRF via withCredentials
- **Fix:** `npm install axios@1.6.0`

### INFO — express@4.18.2
- No known CVEs. Current version is 4.19.2 — consider updating.
```

---

### Secrets scan section

```markdown
## Secrets and exposure scan

### CRITICAL — Hardcoded API key
**File:** `src/config/database.js`, line 12

**Found:** `STRIPE_SECRET_KEY = "sk_live_FAKE_KEY_..."`

**Action required:**
1. Rotate this key immediately at https://dashboard.stripe.com
2. Remove from source code
3. Load via `process.env.STRIPE_SECRET_KEY` from `.env`
4. Add `.env` to `.gitignore`
5. Audit git history — key may be in previous commits:
   `git log --all -p | grep "sk_live_"`
   Use git-filter-repo or BFG to purge from history if found.
```

---

### Patch proposals section

Only for CRITICAL and HIGH findings:

````markdown
## Patch proposals

> Review each patch before applying. Nothing has been changed yet.

### Patch 1/3: SQL injection in `src/routes/users.js`

**Before (vulnerable):**
```js
// Line 47
const query = `SELECT * FROM users WHERE id = ${req.params.id}`;
db.execute(query);
```

**After (fixed):**
```js
// Line 47 — Fixed: Use parameterized query to prevent SQL injection
const query = 'SELECT * FROM users WHERE id = ?';
db.execute(query, [req.params.id]);
```
````

---

### Footer

```markdown
## Scan coverage
- **Files scanned:** <n>
- **Lines analyzed:** <n>

## Next steps
1. Address all CRITICAL findings immediately
2. Schedule HIGH findings for the current sprint
3. Add MEDIUM/LOW to the security backlog
4. Set up automated re-scanning in CI/CD

**Note:** This is static analysis. It does not execute the application and cannot
detect all runtime vulnerabilities. Pair with dynamic testing (DAST) for full coverage.
```

---

## Confidence ratings guide

Apply to every finding:

| Confidence | When to use |
|------------|-------------|
| **High** | Vulnerability is unambiguous. Sanitization is clearly absent. Exploitable as-is. |
| **Medium** | Likely vulnerability but depends on runtime context, config, or untraced call path. |
| **Low** | Suspicious pattern; could be a false positive. Flag for human review. |

Never omit confidence — it helps prioritize review effort.
