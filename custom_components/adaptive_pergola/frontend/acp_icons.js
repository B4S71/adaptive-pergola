// Adaptive Pergola — custom louvred-roof slat iconset.
//
// Served and injected by frontend.py via add_extra_js_url. Registers the "acp"
// icon set so any entity (or cover.py's icon property) can request
// `acp:pergola-slats-<pct>` for pct in {0, 15, 50, 75, 100}. Each glyph draws
// the three slats at the angle matching that open percentage along the pergola's
// non-linear travel curve: 0/15/50/75/100 % -> 0/18/60/90/135 degrees.
//
// The icons are monochrome and use currentColor, so they follow the HA theme
// and go active-coloured when the cover is open, exactly like an MDI icon.

const VIEWBOX = "0 0 24 24";

const PATHS = {
  "pergola-slats-0":
    "M2.55 10.7L7.45 10.7A0.8 0.8 0 0 1 8.25 11.5L8.25 12.5A0.8 0.8 0 0 1 7.45 13.3L2.55 13.3A0.8 0.8 0 0 1 1.75 12.5L1.75 11.5A0.8 0.8 0 0 1 2.55 10.7ZM9.55 10.7L14.45 10.7A0.8 0.8 0 0 1 15.25 11.5L15.25 12.5A0.8 0.8 0 0 1 14.45 13.3L9.55 13.3A0.8 0.8 0 0 1 8.75 12.5L8.75 11.5A0.8 0.8 0 0 1 9.55 10.7ZM16.55 10.7L21.45 10.7A0.8 0.8 0 0 1 22.25 11.5L22.25 12.5A0.8 0.8 0 0 1 21.45 13.3L16.55 13.3A0.8 0.8 0 0 1 15.75 12.5L15.75 11.5A0.8 0.8 0 0 1 16.55 10.7Z",
  "pergola-slats-15":
    "M3.07 10.01L7.73 11.52A0.8 0.8 0 0 1 8.25 12.53L7.94 13.48A0.8 0.8 0 0 1 6.93 13.99L2.27 12.48A0.8 0.8 0 0 1 1.75 11.47L2.06 10.52A0.8 0.8 0 0 1 3.07 10.01ZM10.07 10.01L14.73 11.52A0.8 0.8 0 0 1 15.25 12.53L14.94 13.48A0.8 0.8 0 0 1 13.93 13.99L9.27 12.48A0.8 0.8 0 0 1 8.75 11.47L9.06 10.52A0.8 0.8 0 0 1 10.07 10.01ZM17.07 10.01L21.73 11.52A0.8 0.8 0 0 1 22.25 12.53L21.94 13.48A0.8 0.8 0 0 1 20.93 13.99L16.27 12.48A0.8 0.8 0 0 1 15.75 11.47L16.06 10.52A0.8 0.8 0 0 1 17.07 10.01Z",
  "pergola-slats-50":
    "M4.9 9.23L7.35 13.47A0.8 0.8 0 0 1 7.06 14.56L6.19 15.06A0.8 0.8 0 0 1 5.1 14.77L2.65 10.53A0.8 0.8 0 0 1 2.94 9.44L3.81 8.94A0.8 0.8 0 0 1 4.9 9.23ZM11.9 9.23L14.35 13.47A0.8 0.8 0 0 1 14.06 14.56L13.19 15.06A0.8 0.8 0 0 1 12.1 14.77L9.65 10.53A0.8 0.8 0 0 1 9.94 9.44L10.81 8.94A0.8 0.8 0 0 1 11.9 9.23ZM18.9 9.23L21.35 13.47A0.8 0.8 0 0 1 21.06 14.56L20.19 15.06A0.8 0.8 0 0 1 19.1 14.77L16.65 10.53A0.8 0.8 0 0 1 16.94 9.44L17.81 8.94A0.8 0.8 0 0 1 18.9 9.23Z",
  "pergola-slats-75":
    "M6.3 9.55L6.3 14.45A0.8 0.8 0 0 1 5.5 15.25L4.5 15.25A0.8 0.8 0 0 1 3.7 14.45L3.7 9.55A0.8 0.8 0 0 1 4.5 8.75L5.5 8.75A0.8 0.8 0 0 1 6.3 9.55ZM13.3 9.55L13.3 14.45A0.8 0.8 0 0 1 12.5 15.25L11.5 15.25A0.8 0.8 0 0 1 10.7 14.45L10.7 9.55A0.8 0.8 0 0 1 11.5 8.75L12.5 8.75A0.8 0.8 0 0 1 13.3 9.55ZM20.3 9.55L20.3 14.45A0.8 0.8 0 0 1 19.5 15.25L18.5 15.25A0.8 0.8 0 0 1 17.7 14.45L17.7 9.55A0.8 0.8 0 0 1 18.5 8.75L19.5 8.75A0.8 0.8 0 0 1 20.3 9.55Z",
  "pergola-slats-100":
    "M7.65 11.19L4.19 14.65A0.8 0.8 0 0 1 3.06 14.65L2.35 13.94A0.8 0.8 0 0 1 2.35 12.81L5.81 9.35A0.8 0.8 0 0 1 6.94 9.35L7.65 10.06A0.8 0.8 0 0 1 7.65 11.19ZM14.65 11.19L11.19 14.65A0.8 0.8 0 0 1 10.06 14.65L9.35 13.94A0.8 0.8 0 0 1 9.35 12.81L12.81 9.35A0.8 0.8 0 0 1 13.94 9.35L14.65 10.06A0.8 0.8 0 0 1 14.65 11.19ZM21.65 11.19L18.19 14.65A0.8 0.8 0 0 1 17.06 14.65L16.35 13.94A0.8 0.8 0 0 1 16.35 12.81L19.81 9.35A0.8 0.8 0 0 1 20.94 9.35L21.65 10.06A0.8 0.8 0 0 1 21.65 11.19Z",
};

function getIcon(name) {
  const path = PATHS[name];
  if (!path) {
    return Promise.reject(new Error(`acp iconset: unknown icon "${name}"`));
  }
  return Promise.resolve({ path, viewBox: VIEWBOX });
}

// Record-style registry (Home Assistant 2021.10+).
window.customIcons = window.customIcons || {};
window.customIcons["acp"] = { getIcon };

// Function-style registry kept for older frontends; harmless when unused.
window.customIconsets = window.customIconsets || {};
window.customIconsets["acp"] = (name) => getIcon(name);
