# Web UI

The Web UI is served directly by `backend/webui_server.py`. It has no runtime
build step and must remain fully usable offline.

## Layout

- `index.html` — application shell
- `assets/css/` — Enchan tokens, layout, components, and status styles
- `assets/js/` — chat, appearance, localization, and status behavior
- `assets/icons/` — locally bundled interface icons
- `data/` — non-localized UI manifests such as themes
- `locales/` — locale manifest and message catalogs
- `mascots/` — bundled mascot assets
- `vendor/` — narrowly scoped third-party browser components and licenses
- `tools/` — Web UI validation scripts

## Add a language

1. Copy `locales/en.json` to a new locale file and translate every value.
2. Add its code, native display label, and filename to `locales/manifest.json`.
3. Run `python backend/webui/tools/validate_locales.py` from the repository root.

The language Select is populated from the manifest; `index.html` does not need
to change when a locale is added. Set `"dir": "rtl"` on a manifest entry for a
right-to-left locale.

## UI components

Select menus use a local, minimal bundle of Web Awesome 3.2.1. Only Select and
Option are bundled. The Web UI does not load third-party code from a CDN.
