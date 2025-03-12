#!/bin/bash
# Run the test suite with coverage

# Set up Python path
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Make sure pytest-cov is installed
pip install pytest pytest-cov

# Run pytest with coverage
if [[ "$1" == "--verbose" || "$1" == "-v" ]]; then
  poetry run pytest tests/ -v --cov=farsight2 --cov-report=term --cov-report=html
else
  poetry run pytest tests/ --cov=farsight2 --cov-report=term --cov-report=html
fi

# Store the exit code
TEST_EXIT_CODE=$?

# Display coverage report location
echo "Coverage report generated at 'htmlcov/index.html'"

# Return the test exit code
exit $TEST_EXIT_CODE 