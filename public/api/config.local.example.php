<?php
declare(strict_types=1);

// Template for api/config.local.php — copy it, don't rename it:
//
//     cp api/config.local.example.php api/config.local.php
//
// config.local.php is gitignored and per-install: your laptop and the server each get
// their own, with different values. Every setting below is optional; the app runs with
// none of them. _appdb.php loads the file if it exists, before it decides anything.
//
// ⚠ When deploying, do NOT copy your local config.local.php over the server's:
//
//     rsync -av --exclude 'api/config.local.php' public/ you@host:~/site/


// ── Where writable data lives ─────────────────────────────────────────────────
//
// app.db and secret.key go here. Defaults to <parent of public/>/private, which is
// correct when public/ IS the web root — and wrong when the app sits in a subfolder,
// because then the parent is the document root and app.db becomes a public download.
// Set this explicitly on any subfolder install. See "Deploying to a subfolder" in
// CLAUDE.md.

// define('OTIOS_PRIVATE_DIR', '/home/you/voroave-private');


// ── Moderation ────────────────────────────────────────────────────────────────
//
// Unlocks public/admin.php, the review queue for reported public lists. With this
// undefined the page returns 404 and there is no way in — which is the right state
// for an install that doesn't publish lists.
//
// Generate one and keep it in a password manager; it is the only credential:
//
//     openssl rand -hex 24
//
// Anything shorter than 16 characters is rejected, so a placeholder can't accidentally
// become the password. Rotate by changing the value — sessions are sealed with the
// app secret, not the token, so old browser sessions survive a rotation until they
// expire (8h). To cut them off immediately, delete private/secret.key as well.

// define('OTIOS_ADMIN_TOKEN', 'replace-me-with-openssl-rand-hex-24');


// ── Quiz signing ──────────────────────────────────────────────────────────────
//
// Overrides the auto-generated private/secret.key used to seal quiz tokens and admin
// sessions. Only needed if you run more than one web node and they must agree.

// define('OTIOS_QUIZ_SECRET', '...');
