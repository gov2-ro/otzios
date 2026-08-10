<?php
declare(strict_types=1);
require_once __DIR__ . '/_auth.php';

$sort      = trim($_GET['sort']      ?? '');
$page      = max(1, (int)($_GET['page'] ?? 1));
$offset    = ($page - 1) * PAGE_SIZE;
$marks     = trim($_GET['marks']     ?? 'all');
$q         = trim($_GET['q']         ?? '');
$marked_words_raw = trim($_GET['marked_words'] ?? '');
$marked_words = $marked_words_raw !== ''
    ? array_filter(array_map('trim', explode(',', $marked_words_raw)))
    : [];

// Playlist (`w=` packed, or the legacy plaintext `words=`) — see playlist_words().
$playlist = playlist_words($_GET);

// Build the shared server-side filters — unless a playlist is open.
//
// A playlist is a list someone chose by hand: a shared list opened from lista.php, a
// published bucket, a set of bookmarks. Running the default filters over it silently
// subtracts from what the sender picked — the default view alone hides regionalisms,
// old variants, proper nouns and the whole `curiosity` seam, so a shared list of twenty
// words could arrive showing eleven, with nothing on the page to say why. Whoever
// assembled the list has already done the filtering; `w=` means show exactly these.
//
// `q` and `marks` below still apply: those are things the *reader* just typed or picked,
// not defaults they never chose. The UI dims the filter sheet while a playlist is open
// (see setPlaylistMode() in app.js) so the two halves agree.
$conditions = [];
$params     = [];
if ($playlist === null) {
    ['conditions' => $conditions, 'params' => $params] = build_word_filter($_GET);
} else {
    playlist_condition($playlist, $conditions, $params);
}

// search-only: text search
if ($q !== '') {
    $q_norm       = normalize_diacritics($q);
    $conditions[] = '(word LIKE ? OR word_normalized LIKE ?)';
    $params[]     = '%' . $q . '%';
    $params[]     = '%' . $q_norm . '%';
}

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
$is_mark_filter = in_array($marks, ['bookmarked', 'noted', 'marked', 'unmarked'], true)
                  || str_starts_with($marks, 'tag:');

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
$order_by = $SORT_OPTIONS[$sort] ?? $SORT_OPTIONS[$default_sort];

// Count total matching rows
$count_sql  = "SELECT COUNT(*) FROM words $where";
$count_stmt = db()->prepare($count_sql);
$count_stmt->execute($params);
$total = (int)$count_stmt->fetchColumn();

// Fetch page
$page_stmt = db()->prepare("SELECT * FROM words $where ORDER BY $order_by LIMIT ? OFFSET ?");
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
