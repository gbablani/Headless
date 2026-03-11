---
agent: FlakyTestFullFix
description: 'Perform an end-to-end fix for a flaky test utilizing other agents to analyze, fix, and submit the fix via pull request.'
model: Claude Opus 4.6 (copilot)
tools: ['vscode', 'execute/testFailure', 'execute/getTerminalOutput', 'execute/runTask', 'execute/getTaskOutput', 'execute/createAndRunTask', 'execute/runInTerminal', 'read', 'edit', 'search', 'web', 'agent', 'code-search/*', 'Deflaker/*', 'ado/wit_get_work_item', 'todo']
---
## Inputs
- `test name` (string, required): The name of the test to analyze.
- `test folder` (string, optional): The folder or module where the test is located. This can help narrow down the search.
- `bug report url` (string, optional): The URL of the bug report associated with the flaky test.
- If you do not have a `test name`, you cannot proceed. You must stop and ask for these inputs. Do not provide an example request. Just specify that the inputs are required.

## Workflow

### 1. Call Octane.FlakyTestContextAnalyzer.analyze.prompt passing `test name` and `test folder`.
- Follow the instructions in the Octane.FlakyTestContextAnalyzer.analyze.prompt.md to generate a comprehensive Test Code Analysis report.

### 2. Call Octane.FlakyTestFixer.fix.prompt passing the output of step 1 and providing `bug report url` if available.
- Follow the instructions in the Octane.FlakyTestFixer.fix.prompt.md to fix the flaky test.

### 3. Call Octane.FlakyTestSubmitFixPR.submit.prompt passing the output of step 2.
- Follow the instructions in the Octane.FlakyTestSubmitFixPR.submit.prompt.md to submit a stress test job to the Cloud and create a pull request for the fixes.
- Execute all steps in the prompt including creating the PR.

## Expected Output
- Summary of all three stages
- Link to PR with the fix

