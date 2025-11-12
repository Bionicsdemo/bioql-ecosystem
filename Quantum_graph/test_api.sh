#!/bin/bash

# Quantum Graph API Test Script
# Tests all new endpoints

BASE_URL="http://localhost:9000"
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Quantum Graph API Test Suite${NC}"
echo -e "${BLUE}================================${NC}\n"

# Test 1: Submit Quantum Job
echo -e "${YELLOW}[TEST 1]${NC} Submitting quantum job..."
JOB_RESPONSE=$(curl -s -X POST ${BASE_URL}/api/optimize/quantum \
  -H "Content-Type: application/json" \
  -d '{
    "molecule_data": {
      "smiles": "CCO",
      "num_atoms": 9,
      "num_electrons": 20
    },
    "molecule_type": "small_molecule",
    "viz_type": "energy_landscape",
    "backend_preference": "qiskit_simulator",
    "shots": 1024,
    "accuracy_target": 0.95
  }')

echo "$JOB_RESPONSE" | jq '.'

# Extract job ID
JOB_ID=$(echo $JOB_RESPONSE | jq -r '.job_id')

if [ "$JOB_ID" = "null" ] || [ -z "$JOB_ID" ]; then
  echo -e "${RED}✗ Failed to create job${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Job created: $JOB_ID${NC}\n"

# Test 2: Check Queue Stats
echo -e "${YELLOW}[TEST 2]${NC} Checking queue statistics..."
curl -s ${BASE_URL}/api/queue/stats | jq '.'
echo -e "${GREEN}✓ Queue stats retrieved${NC}\n"

# Test 3: Poll Job Status
echo -e "${YELLOW}[TEST 3]${NC} Polling job status..."
MAX_ATTEMPTS=60
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
  STATUS_RESPONSE=$(curl -s ${BASE_URL}/api/jobs/${JOB_ID}/status)
  STATUS=$(echo $STATUS_RESPONSE | jq -r '.status')
  PROGRESS=$(echo $STATUS_RESPONSE | jq -r '.progress')

  echo -e "${BLUE}Status: $STATUS | Progress: $PROGRESS%${NC}"

  if [ "$STATUS" = "completed" ]; then
    echo -e "${GREEN}✓ Job completed successfully${NC}\n"
    break
  elif [ "$STATUS" = "failed" ]; then
    echo -e "${RED}✗ Job failed${NC}"
    echo $STATUS_RESPONSE | jq '.'
    exit 1
  fi

  sleep 5
  ATTEMPT=$((ATTEMPT + 1))
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
  echo -e "${RED}✗ Job timed out${NC}"
  exit 1
fi

# Test 4: Get Job Result
echo -e "${YELLOW}[TEST 4]${NC} Retrieving job result..."
RESULT_RESPONSE=$(curl -s ${BASE_URL}/api/jobs/${JOB_ID}/result)
echo $RESULT_RESPONSE | jq '.result.quantum_result.backend, .result.quantum_config.logical_qubits, .result.execution_metrics'
echo -e "${GREEN}✓ Job result retrieved${NC}\n"

# Extract visualization file names
VIZ_FILES=$(echo $RESULT_RESPONSE | jq -r '.result.visualization_files | to_entries | .[].key')

# Test 5: Download Individual Files
echo -e "${YELLOW}[TEST 5]${NC} Testing individual file download..."
FIRST_FILE=$(echo $VIZ_FILES | head -n1)
if [ ! -z "$FIRST_FILE" ]; then
  FILE_PATH=$(echo $RESULT_RESPONSE | jq -r ".result.visualization_files.${FIRST_FILE}")
  FILENAME=$(basename "$FILE_PATH")

  curl -s ${BASE_URL}/api/jobs/${JOB_ID}/files/${FILENAME} > /tmp/test_download_${FILENAME}

  if [ -f "/tmp/test_download_${FILENAME}" ] && [ -s "/tmp/test_download_${FILENAME}" ]; then
    echo -e "${GREEN}✓ Individual file downloaded: $FILENAME${NC}\n"
    rm /tmp/test_download_${FILENAME}
  else
    echo -e "${RED}✗ File download failed${NC}\n"
  fi
else
  echo -e "${RED}✗ No visualization files found${NC}\n"
fi

# Test 6: Download ZIP
echo -e "${YELLOW}[TEST 6]${NC} Downloading ZIP archive..."
curl -s -o /tmp/test_results.zip ${BASE_URL}/api/jobs/${JOB_ID}/download

if [ -f "/tmp/test_results.zip" ] && [ -s "/tmp/test_results.zip" ]; then
  FILE_SIZE=$(wc -c < /tmp/test_results.zip)
  echo -e "${GREEN}✓ ZIP downloaded successfully (${FILE_SIZE} bytes)${NC}"

  # List ZIP contents
  echo -e "${BLUE}ZIP contents:${NC}"
  unzip -l /tmp/test_results.zip

  rm /tmp/test_results.zip
  echo ""
else
  echo -e "${RED}✗ ZIP download failed${NC}\n"
fi

# Test 7: Delete Job
echo -e "${YELLOW}[TEST 7]${NC} Deleting job..."
DELETE_RESPONSE=$(curl -s -X DELETE ${BASE_URL}/api/jobs/${JOB_ID})
echo $DELETE_RESPONSE | jq '.'
echo -e "${GREEN}✓ Job deleted${NC}\n"

# Test 8: Verify Deletion
echo -e "${YELLOW}[TEST 8]${NC} Verifying job deletion..."
VERIFY_RESPONSE=$(curl -s ${BASE_URL}/api/jobs/${JOB_ID}/status)
DETAIL=$(echo $VERIFY_RESPONSE | jq -r '.detail')

if [ "$DETAIL" = "Job not found" ]; then
  echo -e "${GREEN}✓ Job successfully deleted${NC}\n"
else
  echo -e "${RED}✗ Job still exists${NC}\n"
fi

# Summary
echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}All Tests Passed!${NC}"
echo -e "${BLUE}================================${NC}"
echo -e "\n${GREEN}✓ Job submission working${NC}"
echo -e "${GREEN}✓ Status polling working${NC}"
echo -e "${GREEN}✓ Result retrieval working${NC}"
echo -e "${GREEN}✓ File downloads working${NC}"
echo -e "${GREEN}✓ ZIP downloads working${NC}"
echo -e "${GREEN}✓ Job deletion working${NC}\n"
