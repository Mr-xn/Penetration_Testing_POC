#!/bin/bash
cd /Users/macpro/Downloads/qinglong/tmp
# restart the container first to have a clean state before test 12
echo "Restoring clean state for tests..."
docker restart ql-vuln-test > /dev/null
sleep 20
echo "Running all tests in poc_test.py..."
.venv/bin/python3 poc_test.py
