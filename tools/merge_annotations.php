<?php
/**
 * merge_annotations.php — copy one user's word marks from a source app.db into a
 * destination app.db, attributing them to a (possibly different) destination user.
 *
 * Only final state is copied, never history:
 *   - rows with deleted = 1 (tombstones) are skipped — no remote mark is ever removed;
 *   - rows with no tags, no bookmark and no note are skipped — they mark nothing;
 *   - seq values are NOT carried over. seq is the per-user sync cursor (sync.php
 *     allocates MAX(seq)+1 in one transaction), so imported rows are re-numbered
 *     from the destination user's own MAX(seq). Carrying source seqs would leave
 *     rows below a synced client's cursor, never to be delivered.
 *
 * Conflicts on (user_id, word) follow the app's own rule — last write wins by
 * updated_at (the ON CONFLICT guard in sync.php). A remote row with a newer
 * updated_at is left alone.
 *
 * Usage:
 *   php tools/merge_annotations.php --dst path/to/remote-app.db [--src private/app.db]
 *       [--src-user pax1] [--dst-user pax1] [--words-db path/to/ui.db] [--drop-missing] [--apply]
 *
 * Defaults to a dry run; pass --apply to write. Run against a COPY of the remote
 * database (or upload the merged file back). app.db is WAL — when copying it around,
 * take -wal/-shm with it or use `VACUUM INTO` on the server (see api/_backup.php).
 */

$opts = ['src' => 'private/app.db', 'dst' => null, 'src-user' => 'pax1',
         'dst-user' => 'pax1', 'src-id' => null, 'dst-id' => null,
         'words-db' => null, 'drop-missing' => false, 'apply' => false];
for ($i = 1; $i < $argc; $i++) {
    switch ($argv[$i]) {
        case '--src': case '--dst': case '--src-user': case '--dst-user':
        case '--src-id': case '--dst-id': case '--words-db':
            $key = substr($argv[$i], 2);
            if (!isset($argv[++$i])) { fwrite(STDERR, "missing value for {$argv[$i-1]}\n"); exit(1); }
            $opts[$key] = $argv[$i];
            break;
        case '--drop-missing': $opts['drop-missing'] = true; break;
        case '--apply': $opts['apply'] = true; break;
        case '--help': case '-h':
            echo "usage: php tools/merge_annotations.php --dst <app.db> [--src private/app.db]\n"
               . "           [--src-user pax1] [--dst-user pax1] [--words-db ui.db] [--drop-missing] [--apply]\n";
            exit(0);
        default: fwrite(STDERR, "unknown option: {$argv[$i]}\n"); exit(1);
    }
}
if ($opts['dst'] === null) { fwrite(STDERR, "--dst is required\n"); exit(1); }

function open_db(string $path, bool $writable): PDO {
    if (!file_exists($path)) { fwrite(STDERR, "no such file: $path\n"); exit(1); }
    $pdo = new PDO('sqlite:' . $path, null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
    if ($writable) {
        $pdo->exec('PRAGMA busy_timeout = 30000');
        $pdo->exec('PRAGMA journal_mode = WAL');
    } else {
        $pdo->exec('PRAGMA query_only = ON');
    }
    return $pdo;
}

/** Resolve a user by nickname; when several match, pick the one with the most live marks. */
function resolve_user(PDO $pdo, string $nickname, string $which): array {
    $st = $pdo->prepare('SELECT id FROM users WHERE nickname = ? ORDER BY id');
    $st->execute([$nickname]);
    $ids = $st->fetchAll(PDO::FETCH_COLUMN);
    if (!$ids) {
        fwrite(STDERR, "$which user '$nickname' not found\n");
        exit(1);
    }
    if (count($ids) > 1) {
        $counts = [];
        foreach ($ids as $id) {
            $st = $pdo->prepare('SELECT COUNT(*) FROM annotations WHERE user_id = ? AND deleted = 0');
            $st->execute([$id]);
            $counts[$id] = (int) $st->fetchColumn();
        }
        arsort($counts);
        $id = (int) array_key_first($counts);
        fwrite(STDERR, "warning: $which nickname '$nickname' matches " . count($ids)
                     . " users; using id $id (most marks: {$counts[$id]})\n");
        return ['id' => $id, 'count' => $counts[$id]];
    }
    $id = (int) $ids[0];
    $st = $pdo->prepare('SELECT COUNT(*) FROM annotations WHERE user_id = ? AND deleted = 0');
    $st->execute([$id]);
    return ['id' => $id, 'count' => (int) $st->fetchColumn()];
}

$src = open_db($opts['src'], false);
$dst = open_db($opts['dst'], true);

$src_user = $opts['src-id'] !== null
    ? ['id' => (int) $opts['src-id'], 'count' => null]
    : resolve_user($src, $opts['src-user'], 'source');
$dst_user = $opts['dst-id'] !== null
    ? ['id' => (int) $opts['dst-id'], 'count' => null]
    : resolve_user($dst, $opts['dst-user'], 'destination');
$dst_id   = $dst_user['id'];

// Final state only: no tombstones, no rows that mark nothing.
$st = $src->prepare(
    'SELECT word, bookmarked, note, tags, updated_at
       FROM annotations
      WHERE user_id = ? AND deleted = 0
        AND (tags != \'[]\' OR bookmarked != 0 OR note != \'\')
      ORDER BY word'
);
$st->execute([$src_user['id']]);
$rows = $st->fetchAll(PDO::FETCH_ASSOC);

// Everything skipped: tombstones plus live rows that mark nothing.
$st = $src->prepare('SELECT COUNT(*) FROM annotations WHERE user_id = ?');
$st->execute([$src_user['id']]);
$dropped = (int) $st->fetchColumn() - count($rows);

// Words the remote ui.db does not know would be rejected by sync.php's
// filter_existing_words — report them, or drop them with --drop-missing.
if ($opts['drop-missing'] && $opts['words-db'] === null) {
    fwrite(STDERR, "--drop-missing needs --words-db\n");
    exit(1);
}
$unknown = [];
if ($opts['words-db'] !== null) {
    $ui = open_db($opts['words-db'], false);
    $known = [];
    foreach (array_chunk(array_column($rows, 'word'), 400) as $chunk) {
        $ph = implode(',', array_fill(0, count($chunk), '?'));
        $s  = $ui->prepare("SELECT word FROM words WHERE word IN ($ph)");
        $s->execute($chunk);
        foreach ($s->fetchAll(PDO::FETCH_COLUMN) as $w) { $known[$w] = true; }
    }
    foreach ($rows as $r) { if (!isset($known[$r['word']])) { $unknown[] = $r['word']; } }
    if ($opts['drop-missing'] && $unknown) {
        $unknown_set = array_flip($unknown);
        $rows = array_values(array_filter($rows, fn($r) => !isset($unknown_set[$r['word']])));
    }
}

$lookup = $dst->prepare('SELECT bookmarked, note, tags, updated_at FROM annotations WHERE user_id = ? AND word = ?');
$insert = $dst->prepare(
    'INSERT INTO annotations (user_id, word, bookmarked, note, tags, updated_at, seq, deleted)
     VALUES (?, ?, ?, ?, ?, ?, ?, 0)'
);
$update = $dst->prepare(
    'UPDATE annotations
        SET bookmarked = ?, note = ?, tags = ?, updated_at = ?, seq = ?
      WHERE user_id = ? AND word = ?'
);

$dst->beginTransaction();
try {
    $seq = (int) $dst->query("SELECT COALESCE(MAX(seq), 0) FROM annotations WHERE user_id = $dst_id")
                    ->fetchColumn();

    $inserted = $updated = $untouched = 0;
    foreach ($rows as $r) {
        $lookup->execute([$dst_id, $r['word']]);
        $existing = $lookup->fetch(PDO::FETCH_ASSOC);
        if (!$existing) {
            if (!$opts['apply']) { $inserted++; continue; }
            $insert->execute([$dst_id, $r['word'], $r['bookmarked'], $r['note'],
                              $r['tags'], $r['updated_at'], ++$seq]);
            $inserted++;
        } elseif (strcmp($r['updated_at'], $existing['updated_at']) > 0) {
            if (!$opts['apply']) { $updated++; continue; }
            $update->execute([$r['bookmarked'], $r['note'], $r['tags'],
                              $r['updated_at'], ++$seq, $dst_id, $r['word']]);
            $updated++;
        } else {
            $untouched++;
        }
    }
    $dst->commit();
} catch (Throwable $e) {
    $dst->rollBack();
    fwrite(STDERR, "merge failed: {$e->getMessage()}\n");
    exit(1);
}

$quick = $dst->query('PRAGMA quick_check')->fetchColumn();
if ($quick !== 'ok') { fwrite(STDERR, "quick_check on destination: $quick\n"); exit(1); }

echo ($opts['apply'] ? "merged " : "dry run: would merge ") . count($rows) . " rows"
   . " from {$opts['src-user']} (id {$src_user['id']}) into {$opts['dst-user']} (id $dst_id)\n";
echo "  inserted:   $inserted\n";
echo "  updated:    $updated (source newer than destination)\n";
echo "  left alone: $untouched (destination newer or same)\n";
if ($dropped)      { echo "  dropped:    $dropped (tombstones / rows that mark nothing)\n"; }
if ($unknown)      {
    $label = $opts['drop-missing'] ? 'dropped' : 'WARNING';
    echo "  $label: " . count($unknown) . " words not in ui.db: " . implode(', ', $unknown) . "\n";
}
echo "  destination MAX(seq) for this user now: "
   . (int) $dst->query("SELECT COALESCE(MAX(seq), 0) FROM annotations WHERE user_id = $dst_id")->fetchColumn() . "\n";
