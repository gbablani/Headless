---
name: stress-test
description: |
  Stress test execution skill for validating flaky test fixes. Automatically activated when users request any of these tasks:
  - Queue a stress test ("run stress test", "queue stress test", "validate my fix")
  - Verify fix stability ("check if the fix is stable", "test for flakiness")
  - Run tests multiple times ("run tests repeatedly", "stress the test")
---

# Stress Test Skill

This skill provides guidance for running stress tests in a remote build environment to verify that flaky test fixes are stable and the test doesn't fail intermittently under repeated execution.

## Prerequisites

Before running a stress test:
- Local build and test execution must complete successfully

## Steps

### 1. Prepare for Stress Test

Before queuing the stress test:
- **Notify the user**: Ask the user to avoid making any local changes while the stress test is being queued
- **Verify local success**: Confirm the test passes locally before stress testing

### 2. Queue the Stress Test

Use the `queue_stress_test` MCP tool to queue a stress test for the test project.

**Tool:** `queue_stress_test`

**Required Parameter:**
- `TestName`: The name of the test (e.g., `MyNamespace.MyTestClass.MyTestMethod`)
- `StressTestPath`: The path to the test project directory (e.g., `src\Services\DatacenterPlatform\OneMosAgent\UnitTests`)

**What the Tool Does:**
1. Creates a temporary branch with the local changes
2. Queues a CloudBuild job that runs the tests multiple times to detect flakiness
3. Returns a link to monitor the stress test results

### 3. Report Results

After the stress test is successfully queued, inform the user that the stress test has been queued and provide a response similar to what is shown as the example response.

**Example Response:**
```
Stress test queued successfully!
Build URL: https://cloudbuild.microsoft.com/build/a856f369-7d4c-4153-87ba-3e4b552ba078?bq=azure_one_compute
Test Configuration:
- Queue: azure_one_compute
- Test Path: src\Services\DatacenterPlatform\OneMosAgent\UnitTests
- Repository: Azure-Compute
```

## Rules

### User Communication
- **Warn before queuing**: Always inform the user not to make local changes while queuing
- **Provide tracking link**: Always return the CloudBuild URL for monitoring

### Stress Test Execution
- **Run after local success**: Only queue stress tests after local build and tests pass
- **Single execution**: Queue one stress test at a time
- **Monitor results**: Provide the URL so users can track test execution

### PR Integration
- **Document in PR**: Recommend adding the stress test results link to the PR description
- **Reviewer validation**: Reviewers can use the link to verify fix stability

## Failure Handling

| Scenario | Action |
|----------|--------|
| Authentication Issues with Azure DevOps | Report the error and ask the user to restart the Deflaker MCP Tool |
| Tool fails to queue a stress test | Report the error and continue the workflow |
| Local tests not passing | Do not queue; fix local issues first |
| Branch creation fails | Report the error with details |

## Tips

- Add the stress test results link to the PR description for reviewers to validate the fix stability
