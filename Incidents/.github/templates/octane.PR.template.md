---
agent: 'agent'
description: This document provides instructions for AI agents to generate standardized pull request titles and descriptions when fixing flaky tests in the repository.
---

# AI Agent Instructions: Flaky Test Fix Pull Request Title and Description Generation

## Pull Request Title Template
Use the following format for PR titles:
```
(AI Generated) Fix flaky test: [TestMethodName] in [TestClassName]
```

Example:
```
(AI Generated) Fix flaky test: TestVirtualMachineCreation in ComputeServiceTests
```

## Pull Request Description Template

When generating pull request descriptions for flaky test fixes, use the following template:

```markdown
## Flaky Test Fix

### Test Information
**Test Method:** `[TestMethodName]`
**Test Class:** `[TestClassName]`
**Test Project:** `[TestProjectName]`
**Test File Path:** `[RelativePathToTestFile]`

### AI Tool Used Summary
**AI-Model:** [Claude/GPT-4/Other - specify the AI model used]
**AI-Agent:** [Agent name, e.g., flakytest.agent or MCP-based agent]
**AI-Agent-Version:** [Version if available, otherwise N/A]

### Test Intention
<!-- Describe what the test is supposed to validate -->
[Describe the purpose and expected behavior of the test]

### Flakiness Category
<!-- Select the primary category that best describes the root cause and remove other options-->
- [ ] Race Condition
- [ ] Timing/Synchronization Issues
- [ ] External Dependency Flakiness
- [ ] Resource Cleanup Issues
- [ ] Environment-Specific Issues
- [ ] Test Data Isolation Problems
- [ ] Network/Service Connectivity
- [ ] Threading/Concurrency Issues
- [ ] Configuration/Setup Issues
- [ ] Other: [Specify]

### Error Details
<!-- Include stack traces, error messages, or failure patterns if available -->
```
[Paste any error messages, stack traces, or failure logs here]
```

### Root Cause Analysis
<!-- Explain why the test was flaky -->
[Detailed explanation of what was causing the flaky behavior]

### Fix Implementation
<!-- Describe how the fix addresses the root cause -->
[Explain the changes made and why they resolve the flakiness]

### Additional Notes
[Any additional context, considerations, or follow-up items]

### Retrieving Deflaker Agent Version
To automatically retrieve the Deflaker agent version for the "AI Tool Used Summary" section, check the MCP configuration:

**PowerShell:**
```powershell
# Check local workspace configuration first (if MCP server is started from local repo)
if (Test-Path ".vscode\mcp.json") {
    Write-Host "Checking local workspace MCP configuration..."
    Get-Content ".vscode\mcp.json" | Select-String -Pattern "Deflaker@" -Context 2
} else {
    # Fall back to global VS Code MCP configuration
    Write-Host "Checking global MCP configuration..."
    Get-Content "$env:APPDATA\Code\User\mcp.json" | Select-String -Pattern "Deflaker@" -Context 2
}
```

The version will be in the format: `Deflaker@X.YYYY.ZZZ.W` (e.g., `Deflaker@1.2026.107.1`)

**Note:** If you configured the Deflaker MCP server in the local repository's `.vscode\mcp.json` file, the version is extracted from the `args` array (e.g., `"Deflaker@1.2026.107.1"`). Otherwise, it will check the global VS Code configuration.

---
<!-- Metadata for audit and analytics - DO NOT REMOVE -->
**Metadata:**
- Test-Framework: [MSTest/xUnit/TAEF/Other]
- Service-Area: [ServiceName if applicable]
- Confidence-Level: [High/Medium/Low]
- Fix-Complexity: [Simple/Medium/Complex]
- Prompt: [The prompts (or prompt files) used to fix this test]
```

