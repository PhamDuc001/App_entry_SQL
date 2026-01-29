# Testing Strategies Skill

## Overview
This skill teaches comprehensive testing strategies for Python applications including unit, integration, and E2E testing.

## Principles
- **Test Pyramid**: More unit tests, fewer E2E tests
- **Test Isolation**: Tests should be independent
- **Fast Tests**: Tests should run quickly
- **Descriptive Names**: Test names should be clear
- **AAA Pattern**: Arrange, Act, Assert

## Key Capabilities

### 1. Testing Types
- Unit testing with pytest
- Integration testing
- End-to-end testing
- Property-based testing with Hypothesis

### 2. Testing Tools
- pytest (primary framework)
- unittest.mock for mocking
- pytest-mock for enhanced mocking
- Hypothesis for property testing
- pytest-cov for coverage

### 3. Best Practices
- Fixtures for test setup
- Parametrization for data-driven tests
- Markers for test categorization
- Mocking for external dependencies

## When to Use This Skill
Load this skill when:
- Designing test strategy
- Writing unit tests
- Creating integration tests
- Implementing mocking
- Adding property-based tests

## Sections
- `unit-testing.md`: pytest patterns, fixtures, parametrization
- `integration-testing.md`: Database, API testing
- `mocking.md`: unittest.mock, patching strategies
- `property-testing.md`: Hypothesis, fuzz testing
