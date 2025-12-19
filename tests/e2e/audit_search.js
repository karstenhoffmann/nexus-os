/**
 * Visual Audit: Search Happy Path
 *
 * Testet den kritischen Suchpfad der Nexus OS Library.
 *
 * Pruefpunkte (aus DESIGN_SYSTEM.md & PROJECT_BRIEF.md):
 * 1. Suchfeld ist vorhanden und funktional
 * 2. Semantische Suche liefert gruppierte Ergebnisse (keine Duplikate)
 * 3. Evidence-First: source_url wird angezeigt
 * 4. Ergebnisse haben chunk_preview als Kontext
 *
 * Ausfuehrung via Playwright MCP:
 *   - browser_navigate zu /library
 *   - browser_snapshot zur Analyse
 *   - browser_type fuer Sucheingabe
 *   - browser_snapshot zur Ergebnis-Validierung
 *
 * Erwartetes Ergebnis:
 *   - Jedes Dokument erscheint maximal 1x
 *   - Ergebnisse zeigen Titel, URL, Chunk-Preview
 */

const AUDIT_CONFIG = {
  baseUrl: 'http://localhost:8000',
  searchPath: '/library',
  testQuery: 'machine learning',  // Typischer Suchbegriff

  // Selektoren (basierend auf library.html)
  selectors: {
    searchInput: 'input[type="text"][x-model="q"]',
    searchButton: 'button[type="submit"]',
    resultsTable: '.library-table',
    resultRows: '.library-table tbody tr',
    chunkPreview: '.chunk-preview',
    sourceUrl: '.source-url',
  },

  // Akzeptanzkriterien
  acceptance: {
    maxDuplicateRatio: 0.1,  // Max 10% Duplikate erlaubt
    requireSourceUrl: true,   // Evidence-First
    requireChunkPreview: true,
  },
};

/**
 * Analysiert Suchergebnisse auf Duplikate.
 * @param {Array} rows - Array von Ergebnis-Zeilen
 * @returns {Object} - { uniqueCount, duplicateCount, duplicateRatio, duplicateTitles }
 */
function analyzeDuplicates(rows) {
  const titles = rows.map(r => r.title).filter(Boolean);
  const seen = new Set();
  const duplicates = [];

  for (const title of titles) {
    if (seen.has(title)) {
      duplicates.push(title);
    } else {
      seen.add(title);
    }
  }

  return {
    totalCount: titles.length,
    uniqueCount: seen.size,
    duplicateCount: duplicates.length,
    duplicateRatio: titles.length > 0 ? duplicates.length / titles.length : 0,
    duplicateTitles: [...new Set(duplicates)],
  };
}

module.exports = { AUDIT_CONFIG, analyzeDuplicates };
