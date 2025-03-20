#!/bin/bash

# Farsight2 Test Suite Generator
# This script makes HTTP calls to generate a complete test suite of documents

API_URL="http://localhost:8000/process"
TICKERS=("AAPL" "MSFT" "GOOG" "AMZN" "TSLA")
YEARS=(2020 2021 2022 2023)
QUARTERS=(1 2 3 4)
FILING_TYPES=("10-K" "10-Q")

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo "Starting Farsight2 test suite generation..."
echo "Target API: $API_URL"
echo "----------------------------------------"

# Track statistics
TOTAL=0
SUCCESS=0
FAILED=0

for ticker in "${TICKERS[@]}"; do
  for year in "${YEARS[@]}"; do
    for quarter in "${QUARTERS[@]}"; do
      for filing_type in "${FILING_TYPES[@]}"; do
        TOTAL=$((TOTAL+1))
        
        echo -e "${YELLOW}Processing:${NC} $ticker - $year Q$quarter - $filing_type"
        
        # Prepare JSON payload
        JSON_DATA=$(cat <<EOF
{
  "ticker": "$ticker",
  "year": $year,
  "quarter": $quarter,
  "filing_type": "$filing_type"
}
EOF
)
        
        # Make HTTP request with curl
        RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL" \
          -H "Content-Type: application/json" \
          -d "$JSON_DATA")
        
        # Extract status code
        HTTP_STATUS=$(echo "$RESPONSE" | tail -n1)
        BODY=$(echo "$RESPONSE" | sed '$d')
        
        # Check if request was successful
        if [[ $HTTP_STATUS -ge 200 && $HTTP_STATUS -lt 300 ]]; then
          echo -e "${GREEN}✓ Success${NC} (HTTP $HTTP_STATUS)"
          SUCCESS=$((SUCCESS+1))
        else
          echo -e "${RED}✗ Failed${NC} (HTTP $HTTP_STATUS): $BODY"
          FAILED=$((FAILED+1))
        fi
        
        echo "----------------------------------------"
        
        # Optional: Add a small delay to avoid overwhelming the server
        sleep 10
      done
    done
  done
done

# Print summary
echo "Test Suite Generation Summary:"
echo "-----------------------------"
echo -e "Total requests: $TOTAL"
echo -e "${GREEN}Successful:${NC} $SUCCESS"
echo -e "${RED}Failed:${NC} $FAILED"

# Exit with error code if any requests failed
if [[ $FAILED -gt 0 ]]; then
  exit 1
else
  exit 0
fi
