/**
 * Visual Audit: Home Search Hero
 *
 * Testet das prominente Suchfeld auf der Startseite.
 *
 * Pruefpunkte:
 * 1. Suchfeld ist prominent sichtbar auf /
 * 2. Sucheingabe + Enter leitet zu /library?q=...&mode=... weiter
 * 3. Beide Modi (semantic, fts) werden korrekt uebergeben
 *
 * Ausfuehrung via Playwright MCP:
 *   - browser_navigate zu /
 *   - browser_snapshot zur Analyse (Suchfeld vorhanden?)
 *   - browser_type fuer Sucheingabe
 *   - browser_evaluate zur URL-Validierung
 *
 * Erwartetes Ergebnis:
 *   - URL nach Submit: /library?q=<query>&mode=semantic|fts
 */

const AUDIT_CONFIG = {
  baseUrl: 'http://localhost:8000',
  homePath: '/',
  testQuery: 'test search query',

  // Selektoren (basierend auf home.html)
  selectors: {
    heroSearchWrapper: '.hero-search',
    searchInput: '.hero-search-input',
    modeSelect: '.hero-search-mode',
    submitButton: '.hero-search-form button[type="submit"]',
    searchHint: '.hero-search-hint',
  },

  // Akzeptanzkriterien
  acceptance: {
    requireSearchField: true,
    requireModeSelector: true,
    requireRedirectToLibrary: true,
    requireQueryParam: true,
    requireModeParam: true,
  },
};

/**
 * Validiert die Redirect-URL nach einer Suche.
 * @param {string} url - Die aktuelle URL nach dem Submit
 * @param {string} expectedQuery - Der erwartete Suchbegriff
 * @param {string} expectedMode - Der erwartete Modus (semantic|fts)
 * @returns {Object} - { valid, errors }
 */
function validateRedirectUrl(url, expectedQuery, expectedMode = 'semantic') {
  const errors = [];

  if (!url.includes('/library')) {
    errors.push('URL enthaelt nicht /library');
  }

  const urlObj = new URL(url);
  const q = urlObj.searchParams.get('q');
  const mode = urlObj.searchParams.get('mode');

  if (!q) {
    errors.push('Query-Parameter q fehlt');
  } else if (q !== expectedQuery) {
    errors.push(`Query "${q}" stimmt nicht mit erwartetem "${expectedQuery}" ueberein`);
  }

  if (!mode) {
    errors.push('Mode-Parameter fehlt');
  } else if (mode !== expectedMode) {
    errors.push(`Mode "${mode}" stimmt nicht mit erwartetem "${expectedMode}" ueberein`);
  }

  return {
    valid: errors.length === 0,
    errors,
    parsed: { path: urlObj.pathname, query: q, mode },
  };
}

module.exports = { AUDIT_CONFIG, validateRedirectUrl };
