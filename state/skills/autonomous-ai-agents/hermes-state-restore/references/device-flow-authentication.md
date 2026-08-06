# GitHub device-flow auth via curl — working transcript

Validated 2026-08-06 restoring a private Hermes backup repo on Linux
(`gh` installed but logged out, no credential helper, no SSH keys for GitHub).

## Failure signatures that mean "private repo"
- `git clone https://github.com/<owner>/<repo>.git` →
  `fatal: could not read Username for 'https://github.com': No such device or address`
  (git is about to prompt; private repo).
- `curl -s -o /dev/null -w "%{http_code}" https://github.com/<owner>/<repo>` → `404`
  (GitHub hides private repos from unauthenticated requests; a public
  non-existent repo gives the same 404, so the git username-prompt is the
  deciding signal).

## Exact commands used

1. Request device code (client_id is the gh CLI's public, non-secret id):

```bash
curl -s -X POST https://github.com/login/device/code \
  -H "Accept: application/json" \
  -d "client_id=178c6fc778ccc68e1d6a&scope=repo,workflow,read:org" \
  | tee /tmp/gh_device.json
```

Response: `{"device_code":"...","user_code":"85EF-6DEB","verification_uri":"https://github.com/login/device","expires_in":899,"interval":5}`

2. Give the user: URL `https://github.com/login/device` + code `85EF-6DEB`
   (code valid 15 min; phone browser fine).

3. Poll (background, 5s interval, 180 tries):

```bash
CODE=$(python3 -c "import json;print(json.load(open('/tmp/gh_device.json'))['device_code'])")
for i in $(seq 1 180); do
  RESP=$(curl -s -X POST https://github.com/login/oauth/access_token \
    -H "Accept: application/json" \
    -d "client_id=178c6fc778ccc68e1d6a&device_code=$CODE&grant_type=urn:ietf:params:oauth:grant-type:device_code")
  echo "$RESP" > /tmp/gh_token.json
  echo "$RESP" | grep -q access_token && { echo AUTHORIZED; break; }
  echo "$RESP" | grep -qE "expired_token|access_denied" && { echo "FAILED: $RESP"; break; }
  sleep 5
done
```

4. Seed gh + git once authorized:

```bash
TOKEN=$(python3 -c "import json;print(json.load(open('/tmp/gh_token.json'))['access_token'])")
echo "$TOKEN" | gh auth login --with-token
gh auth setup-git          # credential helper for git over https
gh auth status             # confirm; token stored in system keyring
gh api user --jq .login    # confirm account
```

5. Cleanup: delete /tmp/gh_token.json and /tmp/gh_device.json.

## Notes
- Scopes `repo,workflow,read:org` mirror gh's default token scopes.
- `gh auth setup-git` makes later `git clone` of private repos work with no
  prompts — no PAT ever appears in chat or on disk in plaintext.
- If the user prefers, `gh auth login` interactively is the alternative, but in
  an agent-driven CLI the curl device flow is fully controllable and lets the
  agent show the code and poll in the background.
