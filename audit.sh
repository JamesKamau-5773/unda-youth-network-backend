#!/bin/bash

# Lighthouse audit script for responsive design validation

REPORTS_DIR="./lighthouse-reports"
mkdir -p "$REPORTS_DIR"

echo "=== Running Lighthouse Mobile Audits ==="

pages=(
  "http://127.0.0.1:5000/auth/login:login"
  "http://127.0.0.1:5000/admin/dashboard:admin-dashboard"
  "http://127.0.0.1:5000/admin/manage-assignments:manage-assignments"
  "http://127.0.0.1:5000/admin/users:users"
  "http://127.0.0.1:5000/supervisor/dashboard:supervisor-dashboard"
)

for page in "${pages[@]}"; do
  IFS=':' read -r url name <<< "$page"
  echo "Auditing: $name ($url)"
  
  lighthouse "$url" \
    --preset=mobile \
    --output=json \
    --output-path="$REPORTS_DIR/${name}.json" \
    --chrome-flags="--headless=new --no-sandbox" \
    --quiet 2>/dev/null
  
  if [ -f "$REPORTS_DIR/${name}.json" ]; then
    # Extract scores
    perf=$(jq '.categories.performance.score // "N/A"' "$REPORTS_DIR/${name}.json")
    a11y=$(jq '.categories.accessibility.score // "N/A"' "$REPORTS_DIR/${name}.json")
    best=$(jq '.categories["best-practices"].score // "N/A"' "$REPORTS_DIR/${name}.json")
    seo=$(jq '.categories.seo.score // "N/A"' "$REPORTS_DIR/${name}.json")
    pwa=$(jq '.categories.pwa.score // "N/A"' "$REPORTS_DIR/${name}.json")
    
    echo "  ✓ Performance: $(echo "scale=2; $perf * 100" | bc -l)% | Accessibility: $(echo "scale=2; $a11y * 100" | bc -l)% | Best Practices: $(echo "scale=2; $best * 100" | bc -l)% | SEO: $(echo "scale=2; $seo * 100" | bc -l)% | PWA: $(echo "scale=2; $pwa * 100" | bc -l)%"
  else
    echo "  ✗ Failed to generate report"
  fi
done

echo ""
echo "=== Summary ==="
echo "Reports saved to: $REPORTS_DIR"
echo "To view detailed metrics, run: jq . $REPORTS_DIR/<name>.json"
