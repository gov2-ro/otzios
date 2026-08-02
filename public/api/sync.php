<?php
declare(strict_types=1);
require_once __DIR__ . '/_auth.php';

// Two-way delta sync of the research store (bookmarks / notes / tags), in one call:
//
//   POST { since: <int seq>, changes: [{word, bookmarked, note, tags[], updated_at, deleted}] }
//    →   { server_seq, server_time, changes: [...], applied, rejected, has_more }
//
// The delta cursor is `seq`, a per-user monotonic counter — not a timestamp. PHP has
// no sub-second clock resolution here, so a timestamp cursor would silently skip any
// change written in the same second as the previous sync.
//
// Conflict resolution is separately last-write-wins on `updated_at`, which the client
// store already records. Deletes travel as tombstones (deleted = 1) so they propagate
// to the user's other devices instead of being resurrected by the next push.

require_method('POST');
require_post_same_origin();

$user    = current_user();
$user_id = (int) $user['id'];

if (!rate_limit($user_id, 'sync', 30, 60)) {
    json_out(['error' => 'rate_limited'], 429);
}

const SYNC_PAGE = 5000;

$in      = json_input();
$since   = max(0, (int) ($in['since'] ?? 0));
$changes = is_array($in['changes'] ?? null) ? $in['changes'] : [];
if (count($changes) > SYNC_PAGE) {
    $changes = array_slice($changes, 0, SYNC_PAGE);
}

/**
 * Reject unparseable timestamps, and clamp future ones so a client can't pin LWW
 * forever by sending the year 3000.
 *
 * Must preserve milliseconds: strtotime()/gmdate() would round to whole seconds, and
 * two edits to the same word within one second would then compare equal — the later
 * one losing the `excluded.updated_at > annotations.updated_at` test and being
 * silently dropped.
 */
function clean_ts(mixed $raw): string {
    $utc = new DateTimeZone('UTC');
    $now = new DateTimeImmutable('now', $utc);

    if (!is_string($raw) || $raw === '') return $now->format(TS_FORMAT);
    try {
        $dt = (new DateTimeImmutable($raw))->setTimezone($utc);
    } catch (Exception $e) {
        return $now->format(TS_FORMAT);
    }
    return $dt > $now->modify('+60 seconds') ? $now->format(TS_FORMAT) : $dt->format(TS_FORMAT);
}

$pdo      = app_db();
$applied  = 0;
$rejected = 0;

if ($changes !== []) {
    $incoming = array_values(array_filter(array_map(
        fn($c) => is_array($c) && is_string($c['word'] ?? null) ? $c['word'] : null,
        $changes
    )));
    $valid = filter_existing_words($incoming);

    // Soft quota: once a user is at the cap, existing words can still be edited but
    // no new ones are accepted.
    $stmt = $pdo->prepare('SELECT COUNT(*) FROM annotations WHERE user_id = ? AND deleted = 0');
    $stmt->execute([$user_id]);
    $at_cap = (int) $stmt->fetchColumn() >= MAX_WORDS_PER_USER;

    $present = [];
    if ($at_cap && $incoming !== []) {
        foreach (array_chunk($incoming, 400) as $chunk) {
            $ph = implode(',', array_fill(0, count($chunk), '?'));
            $st = $pdo->prepare("SELECT word FROM annotations WHERE user_id = ? AND word IN ($ph)");
            $st->execute(array_merge([$user_id], $chunk));
            foreach ($st->fetchAll(PDO::FETCH_COLUMN) as $w) { $present[$w] = true; }
        }
    }

    $upsert = $pdo->prepare(
        'INSERT INTO annotations (user_id, word, bookmarked, note, tags, updated_at, seq, deleted)
         VALUES (:uid, :word, :bm, :note, :tags, :ts, :seq, :del)
         ON CONFLICT(user_id, word) DO UPDATE SET
            bookmarked = excluded.bookmarked,
            note       = excluded.note,
            tags       = excluded.tags,
            updated_at = excluded.updated_at,
            seq        = excluded.seq,
            deleted    = excluded.deleted
         WHERE excluded.updated_at > annotations.updated_at'
    );

    $pdo->beginTransaction();
    try {
        // Allocate sequence numbers inside the transaction so concurrent syncs from
        // two devices can't hand out the same cursor value. Gaps are harmless.
        $stmt = $pdo->prepare('SELECT COALESCE(MAX(seq), 0) FROM annotations WHERE user_id = ?');
        $stmt->execute([$user_id]);
        $seq = (int) $stmt->fetchColumn();

        foreach ($changes as $c) {
            $word = is_array($c) && is_string($c['word'] ?? null) ? $c['word'] : '';
            if ($word === '' || !isset($valid[$word]) || ($at_cap && !isset($present[$word]))) {
                $rejected++;
                continue;
            }

            $tags = [];
            if (is_array($c['tags'] ?? null)) {
                foreach (array_slice($c['tags'], 0, MAX_TAGS_PER_WORD) as $t) {
                    if (is_string($t) && trim($t) !== '') {
                        $tags[] = mb_substr(trim($t), 0, MAX_TAG_LEN);
                    }
                }
            }

            $upsert->execute([
                ':uid'  => $user_id,
                ':word' => $word,
                ':bm'   => !empty($c['bookmarked']) ? 1 : 0,
                ':note' => mb_substr(is_string($c['note'] ?? null) ? $c['note'] : '', 0, MAX_NOTE_LEN),
                ':tags' => json_encode(array_values(array_unique($tags)), JSON_UNESCAPED_UNICODE),
                ':ts'   => clean_ts($c['updated_at'] ?? null),
                ':seq'  => ++$seq,
                ':del'  => !empty($c['deleted']) ? 1 : 0,
            ]);
            $applied++;
        }
        $pdo->commit();
    } catch (Throwable $e) {
        $pdo->rollBack();
        throw $e;
    }
}

// Pull everything the server has learned since the client last asked. This echoes
// back the rows just pushed, which is harmless — the client only applies a change
// whose updated_at beats its local copy.
$stmt = $pdo->prepare(
    'SELECT word, bookmarked, note, tags, updated_at, seq, deleted
       FROM annotations
      WHERE user_id = ? AND seq > ?
      ORDER BY seq
      LIMIT ' . (SYNC_PAGE + 1)
);
$stmt->execute([$user_id, $since]);
$rows = $stmt->fetchAll();

$has_more = count($rows) > SYNC_PAGE;
if ($has_more) array_pop($rows);

// Advance the cursor only as far as the rows actually handed over, so a truncated
// page never skips the remainder.
$server_seq = $since;
foreach ($rows as $r) { $server_seq = max($server_seq, (int) $r['seq']); }

$out = array_map(fn(array $r) => [
    'word'       => $r['word'],
    'bookmarked' => (bool) $r['bookmarked'],
    'note'       => $r['note'],
    'tags'       => json_decode($r['tags'], true) ?: [],
    'updated_at' => $r['updated_at'],
    'deleted'    => (bool) $r['deleted'],
], $rows);

json_out([
    'server_seq'  => $server_seq,
    'server_time' => now_iso(),
    'changes'     => $out,
    'applied'     => $applied,
    'rejected'    => $rejected,
    'has_more'    => $has_more,
]);
