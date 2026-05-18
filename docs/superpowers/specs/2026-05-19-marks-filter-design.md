# Marks Filter & Annotation Overlay — Design Spec

## Overview

Add a `marks` filter to the word list that defaults to hiding all annotated words
(bookmarked, tagged, or noted), and overlay emoji indicators on marked words when
they are visible.

## Filter bar change

Replace the `show removed` checkbox pill in Row 1 with a `tax-select` dropdown
named `marks`. Same visual style as register/domain/etymology selects.

Default selected option: `unmarked only` (value `unmarked`).

Options:
```
unmarked only   → value: "unmarked"   (default)
all words       → value: "all"
marked only     → value: "marked"
has note        → value: "noted"
tag: ignore     → value: "tag:ignore"
tag: boring     → value: "tag:boring"
tag: funny      → value: "tag:funny"
tag: remove     → value: "tag:remove"
[custom tags]   → value: "tag:<name>"  (populated from tag_suggestions)
```

Active state (`.active` CSS class): highlight when value differs from `"unmarked"`.
Implemented by adding `data-default="unmarked"` to the select element and extending
the existing tax-select JS to use `sel.dataset.default ?? ''` as the threshold.

## Annotation overlay

Each annotated word chip (`.word-row`) gets a `<span class="ann-overlay">` rendered
inside it, absolutely positioned top-right. Does not extend chip width — overlays the
word text.

Emoji mapping:
| Annotation        | Emoji |
|-------------------|-------|
| bookmarked        | ⭐    |
| has note          | 📝    |
| tag: ignore       | 🙈    |
| tag: boring       | 💤    |
| tag: funny        | 😄    |
| tag: remove       | ❌    |
| any other tag     | 🏷️   |

Multiple annotations concatenate left-to-right (e.g. `❌📝`). Order: tags first
(remove → ignore → boring → funny → other), then note, then bookmark.

CSS:
```css
.ann-overlay {
  position: absolute;
  top: 1px;
  right: 2px;
  font-size: 9px;
  line-height: 1;
  letter-spacing: -1px;
  pointer-events: none;
  user-select: none;
}
```

The existing `.annotated::after` blue dot is removed — the emoji overlay replaces it.

The overlay renders unconditionally for annotated words in the template. It only
*appears* when marked words are visible (when `marks ≠ unmarked`), since in the
default view those words are filtered out.

## Backend changes (`ui/app.py`)

### `/search` route

Remove `show_removed` parameter. Add `marks` parameter (default `'unmarked'`).

Add `d['tags']` (list of strings) to each word dict in the results loop — required
so `word_row.html` can map tags to emojis.

Filtering logic (runs after SQL query, before pagination):

```python
def _is_marked(word: str, bmap: dict) -> bool:
    bm = bmap.get(word, {})
    return bool(
        bm.get('bookmarked')
        or (bm.get('note') or '').strip()
        or (bm.get('tags') or '').strip()
    )

# In /search:
marks = request.args.get('marks', 'unmarked').strip()

if bookmarked_only:
    all_rows = [r for r in all_rows if bmap.get(r['word'], {}).get('bookmarked')]
    # bookmarked_only bypasses marks filter — user is already scoping to a subset
else:
    if marks in ('', 'unmarked'):
        all_rows = [r for r in all_rows if not _is_marked(r['word'], bmap)]
    elif marks == 'marked':
        all_rows = [r for r in all_rows if _is_marked(r['word'], bmap)]
    elif marks == 'noted':
        all_rows = [r for r in all_rows if (bmap.get(r['word'], {}).get('note') or '').strip()]
    elif marks.startswith('tag:'):
        tag_filter = marks[4:]
        all_rows = [r for r in all_rows
                    if tag_filter in [t.strip() for t in
                                      (bmap.get(r['word'], {}).get('tags') or '').split(',')
                                      if t.strip()]]
    # marks == 'all' → no filtering
```

## Template changes

### `word_row.html`

- Remove `_annotated` condition from class list and the `.annotated::after` CSS rule
- Drop `has_tags` bool from word dict (superseded by `w.tags` list); keep `has_note`
- Add `ann-overlay` span when word has any annotation; build emoji string from `w.tags`, `w.has_note`, `w.bookmarked`
- Use inline Jinja logic to map tag names to emojis (no macro needed)

### `base.html`

- Replace `show removed` pill with `marks` tax-select in Row 1
- Extend tax-select JS activation logic with `data-default` attribute support
- Remove `show_removed` from any reset or state-sync logic

## What doesn't change

- `bookmarked` pill filter — unchanged behaviour
- `has_def` segmented control — unchanged
- All taxonomy selects (register, domain, etymology) — unchanged
- Quick tag keyboard shortcuts — unchanged
- Detail panel — unchanged
