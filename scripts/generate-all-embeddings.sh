#!/usr/bin/env bash
# Generiert Embeddings fuer alle Dokumente in Batches
# Kosten: ca. $0.03 pro 100 Dokumente (OpenAI text-embedding-3-small)

set -e

BATCH_SIZE=50
DELAY_SECONDS=5
API_URL="http://localhost:8000/admin/embeddings/generate?limit=${BATCH_SIZE}"

echo "=== Embedding-Generierung gestartet ==="
echo "Batch-Groesse: ${BATCH_SIZE}, Pause: ${DELAY_SECONDS}s"
echo ""

while true; do
    # Status abrufen
    stats=$(curl -s http://localhost:8000/admin/embeddings/stats)
    pending=$(echo "$stats" | python3 -c "import sys,json; print(json.load(sys.stdin)['pending'])")
    total=$(echo "$stats" | python3 -c "import sys,json; print(json.load(sys.stdin)['total_documents'])")
    embedded=$(echo "$stats" | python3 -c "import sys,json; print(json.load(sys.stdin)['embedded_documents'])")

    echo "Fortschritt: ${embedded}/${total} (${pending} ausstehend)"

    if [ "$pending" -eq 0 ]; then
        echo ""
        echo "=== Fertig! Alle ${total} Dokumente haben Embeddings. ==="
        break
    fi

    # Batch generieren
    echo "Generiere naechste ${BATCH_SIZE}..."
    result=$(curl -s -X POST "$API_URL")
    processed=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('processed', 0))")
    failed=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('failed', 0))")
    echo "Batch: ${processed} OK, ${failed} fehlgeschlagen"
    echo ""

    # Pause um Rate-Limits zu vermeiden
    echo "Warte ${DELAY_SECONDS}s..."
    sleep ${DELAY_SECONDS}
done
