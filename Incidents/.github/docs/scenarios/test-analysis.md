# Test Analysis Scenario

## Overview

The Test Analysis scenario provides intelligent test result analysis and reporting capabilities. It uses the Tester agent to analyze test runs, identify patterns, and generate actionable insights for improving code quality.

## What's Included

### Agents
- **Tester** - Analyzes test results and generates reports

### Prompts
- **Octane.Tester.TestAnalysis** - Analyze test results and identify issues
- **Octane.Tester.TestRun** - Execute and monitor test runs

### MCP Servers Required
- **code-search** - For analyzing test code and identifying test coverage

## Prerequisites

- Azure DevOps repository configured
- Test suite configured in your project
- Understanding of testing frameworks and practices

## Example Workflows

### Analyze Test Results

1. Open GitHub Copilot Chat
2. Type: `@Octane.Tester.TestAnalysis`
3. The Tester will:
   - Analyze test run results
   - Identify failing tests and patterns
   - Suggest fixes for common test failures
   - Generate test coverage reports

### Run and Monitor Tests

1. Type: `@Octane.Tester.TestRun`
2. The Tester will:
   - Execute test suite
   - Monitor test execution
   - Report on test results
   - Highlight performance issues

## Use Cases

- Analyzing test failures and flaky tests
- Generating test reports
- Identifying test coverage gaps
- Monitoring test suite health
- Improving test quality

## Difficulty

**Intermediate** - Requires understanding of testing frameworks and test analysis

## Tags

`testing` `quality` `analysis` `test-results`
