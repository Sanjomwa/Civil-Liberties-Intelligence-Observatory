#!/bin/bash
# verify-gcp.sh

PROJECT_ID="encoded-joy-485413-k5"
BUCKET="civil-liberties-data"
PROD_DS="civil_liberties_prod"
STAGING_DS="civil_liberties_staging"

echo "🔍 Verification for Kenya Civil Liberties & Censorship Observatory"
echo ""

echo "→ GCS Bucket"
gsutil ls -b gs://$BUCKET && echo "   ✅ Bucket exists" || echo "   ❌ Missing"

echo "→ BigQuery Datasets"
bq ls --project_id=$PROJECT_ID | grep -E "$PROD_DS|$STAGING_DS" && echo "   ✅ Both datasets exist" || echo "   ❌ One or both missing"

echo ""
echo "If you see ✅ above, your infrastructure is ready!"