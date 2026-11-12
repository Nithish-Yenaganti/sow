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
