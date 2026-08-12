<?php
declare(strict_types=1);

/**
 * Skin discovery.
 *
 * A skin is a plain CSS file in public/assets/skins/. Drop one in and it appears
 * in the dropdown on the next request — there is no registry to edit and no
 * build step. Delete it and it disappears, including for anyone whose browser
 * had it selected (see otios_skin_boot()).
 *
 * Two conventions a skin file must follow:
 *
 *   1. Scope every rule under [data-skin="<filename>"]. Every skin file is
 *      loaded on every page; the attribute on <html> decides which one wins.
 *      A file that forgets to scope itself will apply to all skins at once.
 *
 *   2. Declare a display name in a CSS comment near the top of the file, using
 *      an "@skin" tag followed by the label — see assets/skins/_template.css
 *      for a copyable starting point. Without one, the filename is used.
 *
 * "paper" is the built-in null skin: app.css with nothing layered on top. It has
 * no file, which is why it is added by hand below.
 *
 * Loading every skin on every page is deliberate. The alternative — emitting
 * only the active skin's <link> — cannot work without either a cookie round-trip
 * or a JS-injected stylesheet, and the latter reintroduces the flash of unstyled
 * content that the pre-paint boot script exists to prevent. These files are
 * small and this is a tool for trying styles out; if the folder ever grows past
 * a handful, that is the point to reconsider.
 */

define('SKINS_DIR',   __DIR__ . '/../assets/skins');
define('SKINS_URL',   '/assets/skins');
define('DEFAULT_SKIN', 'govuk');
define('BASE_SKIN',    'paper');

/**
 * @return array<string,string> skin id => display label, base skin first.
 */
function otios_skins(): array
{
    static $skins = null;
    if ($skins !== null) return $skins;

    // $skins = [BASE_SKIN => 'Hârtie — editorial'];
    $skins = [BASE_SKIN => 'Alpha'];

    foreach (glob(SKINS_DIR . '/*.css') ?: [] as $path) {
        $id = basename($path, '.css');

        // Leading underscore marks a template or a partial, not a skin.
        if ($id === '' || $id[0] === '_') continue;

        // The id ends up in a data- attribute, a CSS attribute selector and a
        // URL, so validate it rather than trusting whatever the filename is.
        if (!preg_match('/^[a-z0-9][a-z0-9_-]*$/', $id)) continue;

        $skins[$id] = otios_skin_label($path) ?? $id;
    }

    return $skins;
}

/** Read the `@skin <label>` declaration from the top of a skin file. */
function otios_skin_label(string $path): ?string
{
    $head = @file_get_contents($path, false, null, 0, 512);
    if ($head === false) return null;
    if (!preg_match('/@skin\s+(.+)$/mu', $head, $m)) return null;

    // Trim the comment terminator when the declaration is on one line.
    $label = trim(preg_replace('#\*/.*$#u', '', $m[1]) ?? '');
    return $label !== '' ? $label : null;
}

/**
 * <link> tags for every discovered skin.
 *
 * mtime is appended so an edited skin shows up on reload without a hard
 * refresh — this folder exists to be fiddled with.
 */
function otios_skin_links(): string
{
    $out = [];
    foreach (array_keys(otios_skins()) as $id) {
        if ($id === BASE_SKIN) continue;
        $file = SKINS_DIR . '/' . $id . '.css';
        $v    = @filemtime($file) ?: 0;
        $out[] = '<link rel="stylesheet" href="' . BASE . SKINS_URL . '/'
               . rawurlencode($id) . '.css?v=' . $v . '">';
    }
    return implode("\n  ", $out);
}

/**
 * The pre-paint boot script. Runs before first paint so theme, skin and text
 * scale are applied without a flash.
 *
 * The valid skin list is baked in so a skin that has since been deleted from
 * the folder falls back to the default instead of leaving <html> pointing at a
 * stylesheet that no longer exists.
 */
function otios_skin_boot(): string
{
    $ids     = json_encode(array_keys(otios_skins()), JSON_UNESCAPED_UNICODE);
    $default = json_encode(DEFAULT_SKIN);

    return '<script>(function(){try{'
         . 'var d=document.documentElement;'
         . 'var t=localStorage.getItem("otios.theme")||(matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light");'
         . 'd.setAttribute("data-theme",t);'
         . 'var ok=' . $ids . ',s=localStorage.getItem("otios.skin");'
         . 'd.setAttribute("data-skin",ok.indexOf(s)>=0?s:' . $default . ');'
         . 'var z=localStorage.getItem("otios.textscale")||"100";'
         . 'd.style.fontSize=z+"%";'
         . '}catch(e){}})();</script>';
}

/** The skin dropdown. `$class` adds modifiers, e.g. 'skin-select--sm'. */
function otios_skin_select(string $class = ''): string
{
    $skins = otios_skins();
    $cls   = trim('skin-select ' . $class);

    $out = '<select class="' . e($cls) . '" data-skin-select'
         . ' aria-label="Stil vizual" title="Stil vizual"'
         . ' onchange="setSkin(this.value)">';
    foreach ($skins as $id => $label) {
        $out .= '<option value="' . e($id) . '">' . e($label) . '</option>';
    }
    return $out . '</select>';
}
