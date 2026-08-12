<?php
declare(strict_types=1);
require_once __DIR__ . '/_auth.php';

$sort      = trim($_GET['sort']      ?? '');
$page      = max(1, (int)($_GET['page'] ?? 1));
$offset    = ($page - 1) * PAGE_SIZE;
$marks     = trim($_GET['marks']     ?? 'all');
$marked_words_raw = trim($_GET['marked_words'] ?? '');
$marked_words = $marked_words_raw !== ''
    ? array_filter(array_map('trim', explode(',', $marked_words_raw)))
    : [];

// Which rows are in play: a text search (the whole table), a playlist (`w=` packed, or
// the legacy plaintext `words=`), or the filter sheet. See word_scope() in _lib.php —
// both of the first two exist to stop defaults the reader never set from subtracting
// from what they *did* ask for, whether that is a typed query or a list someone shared
// with them. The UI dims the filter sheet in either mode (setSearchMode() /
// setPlaylistMode() in app.js) so the two halves agree.
$conditions = [];
$params     = [];
$scope      = word_scope($_GET, $conditions, $params);

// Marks filter.
//
// This used to be driven entirely by the client, which sent its whole bookmark list
// as a `marked_words` query parameter — fine for a handful of words, but it grows the
// URL without bound and breaks outright past a few hundred bookmarks. Now the
// annotations live server-side, so this is a subquery against the attached app.db.
//
// `marked_words` is still honoured as a fallback for a browser whose local store has
// not synced yet (offline, or a first visit mid-migration), so the filter never
// silently returns nothing.
//
// A text search skips it along with the rest of the sheet: „marcaje" is one more control
// in there, and leaving it live would make the dimmed sheet a lie for exactly one row.
$is_mark_filter = $scope !== 'search'
                  && (in_array($marks, ['bookmarked', 'noted', 'marked', 'unmarked'], true)
                      || str_starts_with($marks, 'tag:'));

if ($is_mark_filter) {
    $negate = $marks === 'unmarked';
    $sub    = null;

    if (attach_app_db()) {
        $user = current_user();
        $sub  = annotated_words_subquery($marks, (int) $user['id']);
    }

    if ($sub !== null) {
        [$sql, $sub_params] = $sub;
        $conditions[] = 'word ' . ($negate ? 'NOT IN' : 'IN') . " ($sql)";
        $params       = array_merge($params, $sub_params);
    } elseif ($marked_words !== []) {
        $placeholders = implode(',', array_fill(0, count($marked_words), '?'));
        $conditions[] = 'word ' . ($negate ? 'NOT IN' : 'IN') . " ($placeholders)";
        $params       = array_merge($params, array_values($marked_words));
    } elseif (!$negate) {
        $conditions[] = '1=0';      // nothing is marked, so nothing matches
    }
    // unmarked with no marks at all = every word, so no condition is added
}

$where    = $conditions ? 'WHERE ' . implode(' AND ', $conditions) : '';
global $SORT_OPTIONS;
// Fall back if this ui.db predates the rescore and has no quality_score column, so an
// old database still serves rather than 500-ing on an unknown column.
$default_sort = db_has_column('quality_score') ? DEFAULT_SORT : 'rare';
if ($sort === '') { $sort = $default_sort; }

// `populare` is the default and blends quality_score with what people marked, so it — and
// only it — needs the vote counts joined in. An install with no app.db (or one we cannot
// attach) falls back to plain quality rather than failing: votes are an enhancement to the
// ordering, never a precondition for serving the list. That fallback matters more now that
// this is the default, which is why it lands on FALLBACK_SORT rather than on
// $default_sort — the latter is `populare` itself, and would loop.
$from = 'words';
if ($sort === 'populare') {
    if (attach_app_db()) {
        $from = 'words LEFT JOIN (' . vote_counts_subquery() . ') v ON v.vote_word = words.word';
    } else {
        $sort = db_has_column('quality_score') ? FALLBACK_SORT : 'rare';
    }
}
$order_by = $SORT_OPTIONS[$sort] ?? $SORT_OPTIONS[FALLBACK_SORT];

// Curator-demoted words sink to the end of whatever order is in force, rather than being
// removed from it. Prefixed to every sort, including the user's chosen one.
$order_by = demote_order_sql($_GET) . $order_by;

// Count total matching rows. Deliberately on `words` alone: the LEFT JOIN is 1:1 (the
// subquery groups by word), so it cannot change the count, and keeping it out means the
// count query is identical on every sort.
$count_sql  = "SELECT COUNT(*) FROM words $where";
$count_stmt = db()->prepare($count_sql);
$count_stmt->execute($params);
$total = (int)$count_stmt->fetchColumn();

// Fetch page. `words.*` rather than `*` so the joined columns stay out of the row.
$page_stmt = db()->prepare("SELECT words.* FROM $from $where ORDER BY $order_by LIMIT ? OFFSET ?");
$page_stmt->execute(array_merge($params, [PAGE_SIZE, $offset]));
$words = $page_stmt->fetchAll();

$next_url = null;
if ($page * PAGE_SIZE < $total) {
    $args         = $_GET;
    $args['page'] = $page + 1;
    $next_url     = BASE . '/api/search.php?' . http_build_query($args);
}

header('Content-Type: text/html; charset=utf-8');
render('word_list.php', [
    'words'    => $words,
    'total'    => $total,
    'page'     => $page,
    'next_url' => $next_url,
]);
