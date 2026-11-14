"""False alarms and misses found by the real-project evals (evals/compliance). Each stays fixed."""

import json

from compliance import licenses
from compliance.scan import _imgs_without_alt, scan

PROFILE = {"categories": ["saas"], "regions": ["eu_uk", "us_ca"], "audience": "consumers", "minors": "adults",
           "charging": "none", "sensitive": ["none"], "contact_email": "a@b.test"}


def project(tmp_path, files: dict[str, str]):
    for name, text in files.items():
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return {f.fingerprint for f in scan(tmp_path, PROFILE)["findings"]}


def test_img_alt_after_arrow_function_in_src():
    jsx = '<Image\n  src={imgs.find(i => i.path === p)?.url || ""}\n  alt={item.name}\n/>'
    assert _imgs_without_alt(jsx) == []
    assert _imgs_without_alt('<img src="/a.png" className="x">') == [1]


def test_img_without_src_is_prose_not_a_tag():
    assert _imgs_without_alt("replace `next/image` with a standard `<img>` tag") == []


def test_spread_props_can_carry_alt():
    assert _imgs_without_alt("<Image className='x' {...props} />") == []


def test_bare_guaranteed_in_prose_is_not_a_claim(tmp_path):
    fps = project(tmp_path, {"post.mdx": "Three levels deep is guaranteed to be a bad idea.\n",
                             "page.tsx": "<p>Guaranteed results in 30 days</p>\n"})
    assert not any("|guaranteed to be" in f for f in fps)
    assert any(f.startswith("claims.unverified|page.tsx|guaranteed results") for f in fps)


def test_template_model_is_not_a_ui_kit(tmp_path):
    fps = project(tmp_path, {"lib/auth.ts": "send({ TemplateModel: { action_url: url } })\n"})
    assert not any(f.startswith("assets.ui_kit") for f in fps)


def test_lockfile_without_license_fields_is_unchecked_not_unknown(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"a": "1", "b": "1"}}))
    (tmp_path / "package-lock.json").write_text(json.dumps({"lockfileVersion": 3, "packages": {
        "": {}, "node_modules/a": {"version": "1"}, "node_modules/b": {"version": "1"}}}))
    deps, problem = licenses.read_npm(tmp_path)
    assert deps == [] and "no license data" in problem


def test_clerk_user_button_covers_delete_and_edit(tmp_path):
    fps = project(tmp_path, {
        "package.json": json.dumps({"dependencies": {"@clerk/nextjs": "6"}}),
        "components/navbar.tsx": 'import { UserButton } from "@clerk/nextjs";\nexport const N = () => <UserButton />;\n'})
    assert "rights.delete_missing" not in fps and "rights.correct_missing" not in fps
    assert "rights.export_missing" in fps


def test_signup_inside_login_file_needs_terms(tmp_path):
    fps = project(tmp_path, {"app/login.tsx": (
        "export function Login({ mode }) { const action = mode === 'signup' ? signUp : signIn;\n"
        "return <form><input type=\"email\" /><input type=\"password\" /></form> }\n")})
    assert "terms.no_clickwrap|app/login.tsx" in fps


def test_signin_form_linking_to_signup_is_not_signup(tmp_path):
    fps = project(tmp_path, {"components/EmailSignIn.tsx": (
        '<form><input type="email" name="email" /><input type="password" /></form>\n<a href="/signin/signup">Sign up</a>\n')})
    assert not any(f.startswith("terms.no_clickwrap") for f in fps)


def test_ai_system_prompt_is_not_a_disclosure(tmp_path):
    fps = project(tmp_path, {
        "package.json": json.dumps({"dependencies": {"openai": "4"}}),
        "lib/chat.tsx": 'const system = "You are a friendly, helpful AI assistant.";\n'})
    assert any(f.startswith("ai.disclosure_missing") for f in fps)
