#!/usr/bin/env bash
# Fetch the two Google Fonts stylesheets the site uses and every woff2 they
# reference, rewriting the @font-face src to a repo-local path.
#
#   bash tools/fetch_fonts.sh public/assets/fonts
#
# Run this only when a font changes — the output is committed, and the point of
# committing it is that a page load makes no third-party request.
#
# The UA matters: without a modern one the css2 API serves ttf instead of woff2.
# Only the `latin` and `latin-ext` subsets are kept — latin-ext is where ă â î ș ț
# live, and the cyrillic/greek/vietnamese cuts are dead weight for a Romanian site.
set -euo pipefail

UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'
OUT="$1"          # public/assets/fonts
mkdir -p "$OUT"

APP='https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,200..900;1,8..60,200..900&family=Public+Sans:ital,wght@0,400..800;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap'
DOC='https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600;700&family=Source+Serif+4:ital,opsz,wght@0,8..60,200..900;1,8..60,200..900&family=JetBrains+Mono:wght@400;500;600&display=swap'

fetch_css () {  # $1 = url, $2 = output css name
  local raw="$OUT/.$2.raw"
  curl -sL -A "$UA" "$1" -o "$raw"

  python3 - "$raw" "$OUT" "$OUT/$2" <<'PY'
import re, sys, os, urllib.request, hashlib

raw, outdir, dest = sys.argv[1], sys.argv[2], sys.argv[3]
css = open(raw, encoding='utf-8').read()

# Split into @font-face blocks so a block can be dropped whole.
blocks = re.findall(r'/\*[^*]*\*/\s*@font-face\s*\{[^}]*\}', css)
kept, seen = [], {}
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')

for b in blocks:
    subset = re.match(r'/\*\s*([\w-]+)\s*\*/', b).group(1)
    if subset not in ('latin', 'latin-ext'):
        continue
    fam = re.search(r"font-family:\s*'([^']+)'", b).group(1)
    style = re.search(r'font-style:\s*(\w+)', b)
    style = style.group(1) if style else 'normal'
    url = re.search(r'url\((https://[^)]+)\)', b).group(1)

    if url in seen:
        name = seen[url]
    else:
        slug = fam.lower().replace(' ', '-')
        h = hashlib.sha1(url.encode()).hexdigest()[:6]
        name = f'{slug}-{style}-{subset}-{h}.woff2'
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        data = urllib.request.urlopen(req).read()
        open(os.path.join(outdir, name), 'wb').write(data)
        seen[url] = name
        print(f'  {name}  {len(data)//1024} KB')

    kept.append(b.replace(url, name))

open(dest, 'w', encoding='utf-8').write('\n'.join(kept) + '\n')
print(f'{dest}: {len(kept)} @font-face blocks')
PY
  rm -f "$raw"
}

echo "app pages:"; fetch_css "$APP" 'app-fonts.css'
echo "doc pages:"; fetch_css "$DOC" 'doc-fonts.css'
