<?php
declare(strict_types=1);
require_once __DIR__ . '/_appdb.php';

// Anonymous device identity. Everything a visitor produces is saved from the first
// interaction — no sign-up, no login wall. The cookie IS the account.
//
// The schema is already shaped for the upgrade path: users.auth_provider /
// auth_subject / email are nullable and devices.user_id is re-pointable, so adding
// "sign in with Google" later merges devices into one user with no migration.

const DEVICE_COOKIE = 'otios_dev';
const DEVICE_TTL    = 400 * 24 * 3600;   // 400 days — the browser maximum

function is_https(): bool {
    return (($_SERVER['HTTPS'] ?? '') !== '' && $_SERVER['HTTPS'] !== 'off')
        || ($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') === 'https';
}

/**
 * BASE as a valid cookie Path.
 *
 * A Path is matched as a byte prefix of the request-URI, and the browser sends that
 * percent-encoded. An install folder with a non-ASCII name — /oțios/ — therefore
 * stores a Path the request path (/o%C8%9Bios/) can never match: the cookie is set,
 * never returned, and every request mints a fresh anonymous identity. Symptom is a
 * game that appears to save nothing, because each answer lands on a different user.
 */
function cookie_base_path(): string {
    if (BASE === '') return '/';
    // Per segment — rawurlencode would eat the separators.
    return implode('/', array_map('rawurlencode', explode('/', BASE))) . '/';
}

function set_device_cookie(string $token): void {
    if (headers_sent()) return;
    setcookie(DEVICE_COOKIE, $token, [
        'expires'  => time() + DEVICE_TTL,
        'path'     => cookie_base_path(),
        'httponly' => true,
        'secure'   => is_https(),
        'samesite' => 'Lax',
    ]);
}

/**
 * Resolve the caller to a user row, creating one on first sight.
 * Only the SHA-256 of the token is stored, so a leaked database does not hand out
 * working session tokens. No endpoint ever trusts a user id from the request body.
 */
function current_user(): array {
    static $user = null;
    if ($user !== null) return $user;

    $pdo   = app_db();
    $now   = now_iso();
    $token = (string) ($_COOKIE[DEVICE_COOKIE] ?? '');

    if ($token !== '' && strlen($token) >= 32) {
        $stmt = $pdo->prepare(
            'SELECT u.*, d.id AS device_id FROM devices d
             JOIN users u ON u.id = d.user_id
             WHERE d.token_hash = ?'
        );
        $stmt->execute([hash('sha256', $token)]);
        if ($row = $stmt->fetch()) {
            $pdo->prepare('UPDATE devices SET last_seen_at = ? WHERE id = ?')
                ->execute([$now, $row['device_id']]);
            $pdo->prepare('UPDATE users SET last_seen_at = ? WHERE id = ?')
                ->execute([$now, $row['id']]);
            set_device_cookie($token);          // sliding expiry
            return $user = $row;
        }
    }

    // Unknown or missing token — mint a fresh identity.
    $token     = rtrim(strtr(base64_encode(random_bytes(32)), '+/', '-_'), '=');
    $public_id = bin2hex(random_bytes(8));

    $pdo->prepare('INSERT INTO users (public_id, created_at, last_seen_at) VALUES (?, ?, ?)')
        ->execute([$public_id, $now, $now]);
    $user_id = (int) $pdo->lastInsertId();

    $pdo->prepare(
        'INSERT INTO devices (user_id, token_hash, user_agent, created_at, last_seen_at)
         VALUES (?, ?, ?, ?, ?)'
    )->execute([
        $user_id,
        hash('sha256', $token),
        mb_substr((string) ($_SERVER['HTTP_USER_AGENT'] ?? ''), 0, 255),
        $now,
        $now,
    ]);

    set_device_cookie($token);

    $stmt = $pdo->prepare('SELECT * FROM users WHERE id = ?');
    $stmt->execute([$user_id]);
    return $user = $stmt->fetch();
}

// ── Request/response helpers ──────────────────────────────────────────────────

function json_out(array $data, int $code = 200): never {
    if (!headers_sent()) {
        http_response_code($code);
        header('Content-Type: application/json; charset=utf-8');
        header('Cache-Control: no-store');
    }
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
    exit;
}

function json_input(): array {
    $raw = file_get_contents('php://input') ?: '';
    if ($raw === '') return [];
    $data = json_decode($raw, true);
    return is_array($data) ? $data : [];
}

/**
 * CSRF defence. The SameSite=Lax cookie already blocks cross-site POSTs in current
 * browsers; this rejects the rest rather than relying on that alone.
 */
function require_post_same_origin(): void {
    if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'GET') return;

    $origin = $_SERVER['HTTP_ORIGIN'] ?? '';
    if ($origin === '' && ($ref = $_SERVER['HTTP_REFERER'] ?? '') !== '') {
        $p = parse_url($ref);
        $origin = isset($p['scheme'], $p['host'])
            ? $p['scheme'] . '://' . $p['host'] . (isset($p['port']) ? ':' . $p['port'] : '')
            : '';
    }
    if ($origin === '') return;   // same-origin fetch() may send neither header

    $host = $_SERVER['HTTP_HOST'] ?? '';
    $self = (is_https() ? 'https://' : 'http://') . $host;
    if (!hash_equals($self, $origin)) {
        json_out(['error' => 'bad_origin'], 403);
    }
}

function require_method(string ...$allowed): void {
    $m = $_SERVER['REQUEST_METHOD'] ?? 'GET';
    if (!in_array($m, $allowed, true)) {
        json_out(['error' => 'method_not_allowed'], 405);
    }
}
