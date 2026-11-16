"""Package checks: lookalike names (offline), and with --online: packages that don't exist, brand-new or barely used
packages, and known vulnerabilities from the free OSV database (https://osv.dev).

Online lookups send only package names and versions to registry.npmjs.org, api.npmjs.org, pypi.org and api.osv.dev.
No API keys. Results are cached in .guarded/cache.json for a day.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from guarded import __version__
from guarded.project import Dep, Project
from guarded.rules import Finding

UA = f"guarded/{__version__} (security check; +https://github.com/Nithish-Yenaganti/sow)"
TIMEOUT = 10
CACHE_TTL = 24 * 3600
NEW_DAYS = 30
RARE_WEEKLY = 200
MAX_LOOKUPS = 400
MAX_VULN_DETAILS = 80

# Popular names that fakes imitate. A dependency one edit away from one of these (and not itself in the list) is flagged.
POPULAR_NPM = """react react-dom next vue nuxt svelte angular express fastify koa hono axios lodash underscore moment dayjs
date-fns zod yup joi typescript webpack vite rollup esbuild babel-loader eslint prettier jest vitest mocha chai
tailwindcss postcss autoprefixer sass styled-components emotion classnames clsx uuid nanoid dotenv cors helmet
body-parser cookie-parser jsonwebtoken bcrypt bcryptjs argon2 passport mongoose mongodb mysql mysql2 pg sequelize prisma
drizzle-orm knex redis ioredis socket.io ws commander yargs chalk debug ora inquirer glob rimraf mkdirp fs-extra
nodemon concurrently cross-env openai anthropic langchain stripe firebase supabase graphql apollo-server
react-router react-router-dom redux react-redux zustand jotai swr immer formik react-hook-form three d3 chart.js
puppeteer playwright cheerio jsdom marked markdown-it dompurify sharp multer nodemailer winston pino morgan
request superagent got node-fetch cross-fetch ky luxon validator qs ramda rxjs core-js tslib semver minimist
colors async bluebird electron react-native expo mdx remark rehype unified recharts framer-motion lucide-react
tsx ts-node eslint-plugin-react husky lint-staged turbo nx lerna yarn pnpm npm motion sonner
preact next-auth next-themes swr zod-to-json-schema react-icons react-query nodemailer bullmq kysely mysql2 sqlite3 better-sqlite3""".split()
POPULAR_PY = """requests numpy pandas scipy matplotlib seaborn scikit-learn tensorflow torch torchvision keras flask django
fastapi uvicorn gunicorn starlette pydantic sqlalchemy alembic psycopg2 psycopg2-binary pymysql redis celery boto3
botocore openai anthropic langchain langchain-core langchain-openai langchain-community llama-index transformers
tokenizers datasets huggingface-hub sentence-transformers tiktoken httpx aiohttp urllib3 certifi beautifulsoup4 lxml
selenium playwright scrapy pillow opencv-python pyyaml toml click typer rich tqdm python-dotenv jinja2 werkzeug
pytest black ruff mypy flake8 isort setuptools wheel pip poetry cryptography pyjwt bcrypt passlib paramiko
streamlit gradio chromadb pinecone-client faiss-cpu qdrant-client weaviate-client tenacity loguru orjson ujson
marshmallow attrs six python-dateutil pytz arrow docker kubernetes google-cloud-storage firebase-admin stripe
twilio sendgrid pymongo motor elasticsearch nltk spacy gensim xgboost lightgbm plotly dash bokeh sympy networkx""".split()


def _dist(a: str, b: str) -> int:
    """Damerau-Levenshtein distance capped at 2 (one swap counts as one edit)."""
    if abs(len(a) - len(b)) > 1:
        return 2
    prev2, prev = None, list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
            if prev2 is not None and i > 1 and j > 1 and ca == b[j - 2] and a[i - 2] == cb:
                cur[j] = min(cur[j], prev2[j - 2] + 1)
        prev2, prev = prev, cur
    return min(prev[-1], 2)


def lookalike(name: str, ecosystem: str) -> str | None:
    if name.startswith("@") or len(name) < 6:
        return None
    pop = POPULAR_NPM if ecosystem == "npm" else POPULAR_PY
    if name in pop:
        return None
    for p in pop:
        if len(p) >= 5 and _dist(name, p) == 1 and p not in name and name not in p \
                and not name.replace("-", "") == p.replace("-", ""):
            return p
    return None


# --- network ------------------------------------------------------------------------------------------------------
class Net:
    def __init__(self, root: Path, fetch=None):
        self.path = root / ".guarded" / "cache.json"
        try:
            self.cache = json.loads(self.path.read_text())
        except (OSError, ValueError):
            self.cache = {}
        self._fetch = fetch or self._http
        self.errors: list[str] = []

    @staticmethod
    def _http(method: str, url: str, body: dict | None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method,
                                     headers={"User-Agent": UA, "Accept": "application/json",
                                              **({"Content-Type": "application/json"} if data else {})})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.status, json.loads(r.read(8_000_000) or b"null")
        except urllib.error.HTTPError as e:
            return e.code, None

    def get(self, url: str, body: dict | None = None):
        key = url + (json.dumps(body, sort_keys=True) if body else "")
        hit = self.cache.get(key)
        if hit and time.time() - hit["t"] < CACHE_TTL:
            return hit["s"], hit["d"]
        try:
            status, data = self._fetch("POST" if body is not None else "GET", url, body)
        except (OSError, ValueError) as e:
            self.errors.append(f"{urllib.parse.urlparse(url).netloc}: {type(e).__name__}")
            return None, None
        if status in (200, 404):
            self.cache[key] = {"t": time.time(), "s": status, "d": data}
        return status, data

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Keep the cache small: drop old entries and big registry documents.
        now = time.time()
        keep = {k: v for k, v in self.cache.items() if now - v["t"] < CACHE_TTL}
        self.path.write_text(json.dumps(keep))


def _npm_info(net: Net, name: str) -> dict:
    q = urllib.parse.quote(name, safe="@")
    status, dl = net.get(f"https://api.npmjs.org/downloads/point/last-week/{q}")
    if status not in (200, 404) or (status == 200 and (not isinstance(dl, dict) or "downloads" not in dl)):
        return {"unknown": True}                       # rate-limited or offline: never guess
    if status == 404:
        status, doc = net.get(f"https://registry.npmjs.org/{q.replace('/', '%2f')}")
        if status == 404:
            return {"missing": True}
        if status != 200:
            return {"unknown": True}
        dl = {"downloads": 0}
    weekly = (dl or {}).get("downloads", 0)
    info = {"weekly": weekly}
    if weekly < RARE_WEEKLY:
        status, doc = net.get(f"https://registry.npmjs.org/{q.replace('/', '%2f')}")
        if status == 404:
            return {"missing": True}
        if status != 200:
            return info
        created = ((doc or {}).get("time") or {}).get("created")
        if created:
            info["created"] = created
        # The cached registry document can be large; keep only what we use.
        key = f"https://registry.npmjs.org/{q.replace('/', '%2f')}"
        if key in net.cache and net.cache[key]["d"]:
            net.cache[key]["d"] = {"time": {"created": created}}
    return info


def _pypi_info(net: Net, name: str) -> dict:
    url = f"https://pypi.org/pypi/{urllib.parse.quote(name)}/json"
    status, doc = net.get(url)
    if status is None:
        return {"unknown": True}
    if status == 404:
        return {"missing": True}
    times = [f.get("upload_time_iso_8601") for files in ((doc or {}).get("releases") or {}).values() for f in files]
    times = sorted(t for t in times if t)
    if url in net.cache:
        net.cache[url]["d"] = {"releases": {"first": [{"upload_time_iso_8601": times[0]}]}} if times else {"releases": {}}
    return {"created": times[0]} if times else {}


def _age_days(iso: str) -> float | None:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - dt).total_seconds() / 86400


SEV = {"CRITICAL": "high", "HIGH": "high", "MODERATE": "medium", "MEDIUM": "medium", "LOW": "low"}


def _vuln_summary(v: dict, dep: Dep) -> tuple[str, str, str | None, str]:
    ids = [a for a in v.get("aliases", []) if a.startswith("CVE-")] or [v.get("id", "")]
    sev = SEV.get(str((v.get("database_specific") or {}).get("severity", "")).upper(), "medium")
    fixed = None
    for aff in v.get("affected", []):
        pkg = aff.get("package") or {}
        if pkg.get("name", "").lower() != dep.name.lower():
            continue
        for rng in aff.get("ranges", []):
            for ev in rng.get("events", []):
                if ev.get("fixed"):
                    fixed = ev["fixed"]
    title = (v.get("summary") or v.get("details", "").split("\n", 1)[0])[:140]
    return ids[0], sev, fixed if fixed else None, title


def check(pj: Project, online: bool, fetch=None) -> tuple[list[Finding], dict]:
    out: list[Finding] = []
    deps = [d for d in pj.deps if d.name not in pj.local_names]
    meta = {"packages": len(deps), "with_versions": sum(1 for d in deps if d.version), "online": online, "errors": []}
    for d in deps:
        near = lookalike(d.name, d.ecosystem)
        if near:
            out.append(Finding("pkg.lookalike", d.name, near, files=[d.source], key=d.ecosystem))
    if not online:
        return out, meta
    net = Net(pj.root, fetch)
    popular = set(POPULAR_NPM) | set(POPULAR_PY)
    lookups = [d for d in deps if d.name not in popular][:MAX_LOOKUPS]
    with ThreadPoolExecutor(8) as ex:
        infos = list(ex.map(lambda d: _npm_info(net, d.name) if d.ecosystem == "npm" else _pypi_info(net, d.name), lookups))
    for d, info in zip(lookups, infos):
        where = "npm" if d.ecosystem == "npm" else "PyPI"
        if info.get("missing"):
            out.append(Finding("pkg.not_found", d.name, where, files=[d.source], key=d.ecosystem))
            out[:] = [f for f in out if not (f.rule == "pkg.lookalike" and f.subject == d.name)]
            continue
        age = _age_days(info["created"]) if info.get("created") else None
        bits = []
        if age is not None and age < NEW_DAYS:
            bits.append(f"was first published {int(age)} days ago")
        if d.ecosystem == "npm" and "weekly" in info and info["weekly"] < RARE_WEEKLY:
            bits.append(f"has {info['weekly']} downloads a week")
        if bits and (age is None or age < NEW_DAYS or info.get("weekly", 1) < 20):
            out.append(Finding("pkg.suspicious", d.name, " and ".join(bits), files=[d.source], key=d.ecosystem))
        if info.get("weekly", 0) > 50_000:
            out[:] = [f for f in out if not (f.rule == "pkg.lookalike" and f.subject == d.name)]
    # Known vulnerabilities (OSV). Only exact versions can be checked.
    versioned = [d for d in deps if d.version]
    vulns: dict[str, list[str]] = {}
    for i in range(0, len(versioned), 500):
        chunk = versioned[i: i + 500]
        q = {"queries": [{"package": {"name": d.name, "ecosystem": d.ecosystem}, "version": d.version} for d in chunk]}
        status, res = net.get("https://api.osv.dev/v1/querybatch", q)
        if status != 200 or not res:
            continue
        for d, r in zip(chunk, res.get("results", [])):
            ids = [v["id"] for v in (r or {}).get("vulns", []) or []]
            if ids:
                vulns[f"{d.ecosystem}:{d.name}@{d.version}"] = ids
    want = list(dict.fromkeys(i for ids in vulns.values() for i in ids))[:MAX_VULN_DETAILS]
    with ThreadPoolExecutor(8) as ex:
        details = dict(zip(want, ex.map(lambda i: net.get(f"https://api.osv.dev/v1/vulns/{i}")[1] or {"id": i}, want)))
    by_key = {f"{d.ecosystem}:{d.name}@{d.version}": d for d in versioned}
    for key, ids in vulns.items():
        d = by_key[key]
        rows, worst, fixes = [], "low", []
        for i in ids:
            v = details.get(i, {"id": i})
            vid, sev, fixed, title = _vuln_summary(v, d)
            rows.append((vid, sev, title))
            if fixed:
                fixes.append(fixed)
            if sev == "high" or (sev == "medium" and worst == "low"):
                worst = sev
        rows = list(dict.fromkeys(rows))
        malware = any(i.startswith("MAL-") for i in ids)
        top = sorted(rows, key=lambda r: {"high": 0, "medium": 1, "low": 2}[r[1]])
        text = "; ".join(f"{vid} ({sev}): {title}" for vid, sev, title in top[:3])
        if len(top) > 3:
            text += f"; and {len(top) - 3} more"
        later = [x for x in fixes if _vkey(x) > _vkey(d.version)]
        if later:
            text += f". Upgrade to {max(later, key=_vkey)} or later to fix all of these."
        if malware:
            text = "it is listed as known malware. Remove it and check the machines that installed it. " + text
            worst = "high"
        out.append(Finding("pkg.vulnerable", f"{d.name} {d.version}", text, files=[d.source],
                           evidence=[r[0] for r in top[:10]], severity=worst, key=d.ecosystem))
    net.save()
    meta["errors"] = net.errors[:5]
    return out, meta


def _vkey(v: str):
    parts = []
    for p in v.replace("-", ".").split("."):
        parts.append((0, int(p)) if p.isdigit() else (1, p))
    return parts
