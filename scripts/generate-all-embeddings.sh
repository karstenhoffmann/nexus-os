#!/usr/bin/env bash
# Generiert Embeddings fuer alle Dokumente in Batches
# Kosten: ca. $0.02 pro 1000 Dokumente (OpenAI text-embedding-3-small)
#
# OpenAI Rate Limits fuer text-embedding-3-small (Dezember 2025):
# - Tier 1: 3,000 RPM (Requests/Min), 1,000,000 TPM (Tokens/Min)
# - Tier 2+: 5,000+ RPM
#
# Bei Batch-Size 100 und 0.2s Delay: ~300 RPM (10% vom Tier 1 Limit)
# Das ist sehr konservativ - bei Bedarf Delay auf 0 setzen.

set -e

BATCH_SIZE=100
DELAY_SECONDS=0.2
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

    # Minimale Pause (0.2s reicht, Tier 1 erlaubt 3000 RPM = 50/Sekunde)
    sleep ${DELAY_SECONDS}
done
