# Farsight2 Test Suite

This directory contains tests for the Farsight2 project.

## Structure

- `unit/`: Unit tests for individual components
- `integration/`: Integration tests that test interactions between components
- `utils/`: Utility functions and mock data for testing
- `conftest.py`: Common fixtures for tests

## Running Tests

To run the tests, use the provided script:

```bash
./scripts/run_tests.sh
```

For verbose output:

```bash
./scripts/run_tests.sh --verbose
```

## Adding Tests

When adding new tests:

1. Place unit tests in the `unit/` directory
2. Place integration tests in the `integration/` directory
3. Use existing fixtures when possible
4. Mock external services and database calls

## Test Coverage

The tests are set up to generate coverage reports. After running the tests, you can view the coverage report at `htmlcov/index.html`.
