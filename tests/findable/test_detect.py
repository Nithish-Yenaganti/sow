from findable.ask import resolve
from findable.detect import detect


def test_nextjs_routes(project):
    root = project("nextjs-app")
    [app] = detect(root)
    assert app.framework == "nextjs-app"
    paths = {r.path: r for r in app.routes}
    assert set(paths) == {"/", "/about", "/features", "/pricing", "/blog/[slug]"}
    assert paths["/features"].file == "app/(marketing)/features/page.tsx"   # route group stripped
    assert paths["/blog/[slug]"].dynamic
    assert app.site_urls == ["https://acme.test"]
    assert app.dev_port == 3100


def test_monorepo_asks_which_app(project):
    root = project("monorepo")
    apps = detect(root)
    assert {a.root for a in apps} == {"apps/web", "apps/docs"}
    res = resolve(root, apps, None, None, check=lambda u: False)
    assert res.questions and res.questions[0].id == "app"
    assert sum(o.recommended for o in res.questions[0].options) == 1


def test_single_prod_url_is_used_without_asking(project):
    root = project("nextjs-app")
    res = resolve(root, detect(root), None, None, check=lambda u: False)
    assert not res.questions and res.url == "https://acme.test"


def test_prod_and_running_dev_server_asks(project):
    root = project("nextjs-app")
    res = resolve(root, detect(root), None, None, check=lambda u: "localhost" in u)
    q = res.questions[0]
    assert q.id == "url"
    assert [o.value for o in q.options] == ["https://acme.test", "http://localhost:3100", "none"]
    assert q.options[0].recommended


def _next_site(d, port=3000):
    (d / "app").mkdir(parents=True)
    (d / "package.json").write_text('{"name": "%s", "dependencies": {"next": "15"}, "scripts": {"dev": "next dev -p %d"}}' % (d.name, port))
    (d / "app" / "page.tsx").write_text("export default function Page() { return <h1>Hi</h1> }")


def test_site_in_top_level_folder_beats_static_root(tmp_path):
    """Bug: a Next.js app in web/ was ignored and the repo root (stray .html files) was scanned."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "notes.html").write_text("<html></html>")
    _next_site(tmp_path / "web")
    apps = detect(tmp_path)
    assert [a.root for a in apps] == ["web"]
    res = resolve(tmp_path, apps, None, "none")
    assert res.app.root == "web"


def test_explicit_app_is_never_replaced(tmp_path):
    """Bug: --app web silently fell back to the root when web/ wasn't in the detected list."""
    (tmp_path / "index.html").write_text("<html><title>root</title></html>")
    _next_site(tmp_path / "client" / "web")          # nested deeper than detection looks
    apps = detect(tmp_path)
    assert [a.root for a in apps] == ["."]
    res = resolve(tmp_path, apps, "client/web", "none")
    assert res.app.root == "client/web" and res.app.framework == "nextjs-app"

    bad = resolve(tmp_path, apps, "nope", "none")
    assert bad.app is None and "nope" in bad.notes[0]


def test_root_site_and_subfolder_site_both_offered(tmp_path):
    _next_site(tmp_path)
    _next_site(tmp_path / "docs", 3001)
    apps = detect(tmp_path)
    assert {a.root for a in apps} == {".", "docs"}
    res = resolve(tmp_path, apps, None, None, check=lambda u: False)
    assert res.questions and res.questions[0].id == "app"


def test_site_in_web_folder_next_to_packages(tmp_path):
    """AgentTwin-like repo: root has index.html and packages/cli, the real site is web/."""
    (tmp_path / "package.json").write_text('{"name": "repo", "private": true}')
    (tmp_path / "index.html").write_text("<svg><title>x</title></svg>")
    cli = tmp_path / "packages" / "cli"
    cli.mkdir(parents=True)
    (cli / "package.json").write_text('{"name": "cli", "dependencies": {"commander": "12"}}')
    _next_site(tmp_path / "web")
    assert [a.root for a in detect(tmp_path)] == ["web"]
