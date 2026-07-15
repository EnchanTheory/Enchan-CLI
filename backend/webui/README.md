# Web UI

The Web UI is served directly by `backend/webui_server.py`. It has no runtime
build step and is fully self-contained at runtime. Browser code, styles, icons,
locales, and UI components are all served from this repository.

The server applies a Content Security Policy that permits resource loading and
API connections only from the local Enchan origin. External scripts, styles,
fonts, images, frames, workers, and HTTP/WebSocket connections are blocked.

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

Select menus and all modal menus use a local, minimal bundle of Web Awesome
3.2.1. Only Select, Option, Dialog, their required dependencies, and the official
Dialog scroll-lock utility are included in `vendor/webawesome/`.

All modal menus use the shared `enchan-dialog` shell: a localized label slot,
an `enchan-dialog-body` content area, and an optional left-aligned
`enchan-dialog-actions` footer. Open and close dialogs through
`window.EnchanDialogs` so individual features do not depend on the native
`HTMLDialogElement` API or duplicate dialog framing styles.
