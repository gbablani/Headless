# Flaky Test Fix Scenario

## Overview

The Flaky Test Fix scenario provides a comprehensive workflow for fixing flaky tests. It uses the FlakyTestContextAnalyzer agent to collect contextual information about the test, uses the FlakyTestFixer agent to propose a fix for the targeted flaky test, and uses the FlakyTestSubmitFixPR agent to create a PR for the fix.

## What's Included

### Agents
- **FlakyTestContextAnalyzer** - Collects contextual information about the test
- **FlakyTestFixer** - Proposes a fix for the test
- **FlakyTestSubmitFixPR** - Creates a PR for the fix
- **FlakyTestFullFix** - Runs an end-to-end process to analyze, propose a fix and create a PR for the fix.

### Prompts
- **Octane.FlakyTestContextAnalyzer.analyze** - Generates a **Test Code Analysis** report providing a comprehensive analysis of the specified test code, including its context, intent, and behavior within the codebase.
- **Octane.FlakyTestFixer.fix** - Produces a minimal, deterministic fix for the given flaky test with high confidence that the fix resolves the flakiness without introducing new issues or changing test intent.
- **Octane.FlakyTestSubmitFixPR.submit** - Generates a Pull Request for the fix and creates PR title and description using predefined templates.
- **Octane.FlakyTestFullFix.Fix** - Orchestrates and triggers all three agents (FlakyTestContextAnalyzer,FlakyTestFixer,FlakyTestSubmitFixPR) to perform an end-to-end fix.

### Templates
- **octane.PR.template** - Template for pull request title and description when submitting flaky test fixes

### MCP Servers Required
- **code-search** - For analyzing codebase structure and searching code
- **Deflaker** - Utilities used by FlakyTestFixer and FlakyTestSubmitFixPR agents
- **azure-devops** - Used to interact with ADO and create pull requests.

## Prerequisites

- Azure DevOps repository configured
- Code Search, Deflaker, and azure-devops MCP servers configured.

## Example Workflows

### Collect contextual information about a flaky test

1. Open GitHub Copilot Chat
2. Type: `@Octane.FlakyTestContextAnalyzer.analyze "test name"`
3. The FlakyTestContextAnalyzer agent will analyze your repository and generate:
   - Test Code Analysis report

### Propose a fix for the flaky test

1. Open GitHub Copilot Chat
2. Type: `@Octane.FlakyTestFixer.fix` (with the test context from the previous step), also add the ADO Bug report URL 
3. The FlakyTestFixer agent will:
   - Analyze the flaky test and its context
   - Identify the root cause of flakiness
   - Propose a minimal, deterministic fix

### Submit a PR for the fix

1. Open GitHub Copilot Chat
2. Type: `@Octane.FlakyTestSubmitFixPR.submit` (with the proposed fix from the previous step)
3. The FlakyTestSubmitFixPR agent will:
   - Create a branch with the fix
   - Generate a PR title and description using the template
   - Submit the pull request

### Trigger an end-to-end process to fix a given flaky test.

1. Open GitHub Copilot Chat
2. Type: `@Octane.FlakyTestFullFix.Fix` "test name", "bug report url"
3. The FlakyTestFullFix agent will trigger a 3 step process:
   - Collect contextual information about a flaky test (FlakyTestContextAnalyzer agent)
   - Propose a fix for the flaky test (FlakyTestFixer agent)
   - Submit a PR for the fix (FlakyTestSubmitFixPR agent)

## Use Cases

- Fixing flaky tests to improve CI/CD reliability
- Analyzing test code to understand flakiness patterns
- Automating the PR creation process for test fixes
- Improving overall test suite stability

## Difficulty

**Intermediate** - Requires understanding of testing frameworks and test analysis

## Tags

`testing` `flaky test` `test health` `test reliability`
