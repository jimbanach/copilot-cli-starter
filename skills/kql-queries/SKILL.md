---
name: kql-queries
description: Write, explain, and debug KQL (Kusto Query Language) queries for Microsoft Sentinel, Defender, and Log Analytics. Use this when asked to write KQL, query logs, investigate security events, or troubleshoot KQL syntax.
---

# KQL Queries

When working with KQL, follow these guidelines:

## 1. Understand the Context
- **Which workspace?** Sentinel, Defender XDR, Log Analytics, Azure Data Explorer
- **What table(s)?** Common tables: `SecurityEvent`, `SigninLogs`, `AuditLogs`, `DeviceEvents`, `EmailEvents`, `OfficeActivity`, `CommonSecurityLog`, `Syslog`
- **Time range?** Default to `| where TimeGenerated > ago(24h)` unless specified
- **Goal?** Detection rule, hunting query, investigation, dashboard visual, or ad-hoc analysis

## 2. Query Structure
Follow this standard pattern:
```kql
TableName
| where TimeGenerated > ago(24h)      // Time filter first
| where <filter conditions>            // Narrow the dataset
| extend <computed columns>            // Add calculated fields
| summarize <aggregations> by <groups> // Aggregate
| sort by <column> desc               // Order results
| project <final columns>             // Select output columns
```

## 3. Best Practices
- **Filter early**: Put `where` clauses before `extend` or `join` to reduce data scanned
- **Use `has` over `contains`**: `has` is case-insensitive and faster (word boundary match)
- **Avoid `*` in project**: Explicitly list columns needed
- **Use `let` for reusable values**: `let threshold = 5;`
- **Comment complex logic**: Use `//` for inline comments
- **Use `arg_min` / `arg_max`** instead of `summarize` + `sort` + `take 1`
- **Use `materialize()`** when referencing the same subquery multiple times

## 4. Common Patterns

### Failed sign-ins by user
```kql
SigninLogs
| where TimeGenerated > ago(7d)
| where ResultType != "0"
| summarize FailureCount = count() by UserPrincipalName, ResultDescription
| sort by FailureCount desc
| take 20
```

### Anomalous process execution
```kql
DeviceProcessEvents
| where TimeGenerated > ago(1d)
| where FileName in~ ("powershell.exe", "cmd.exe", "wscript.exe")
| summarize ExecutionCount = count() by DeviceName, FileName, AccountName
| where ExecutionCount > 50
```

### Multi-table correlation
```kql
let suspiciousUsers = SigninLogs
| where TimeGenerated > ago(1d)
| where ResultType != "0"
| summarize FailCount = count() by UserPrincipalName
| where FailCount > 10
| project UserPrincipalName;
AuditLogs
| where TimeGenerated > ago(1d)
| where InitiatedBy.user.userPrincipalName in (suspiciousUsers)
| project TimeGenerated, OperationName, InitiatedBy, TargetResources
```

## 5. Debugging Queries
When a query has errors:
- Check table name spelling and case
- Verify column names exist in the schema (use `TableName | getschema`)
- Check for missing pipes `|` between operators
- Validate `datetime` and `timespan` formats
- Use `take 10` to test intermediate results

## 6. Output
- Always validate queries against Microsoft Learn docs for current schema
- Include comments explaining the query logic
- Suggest performance optimizations if the query scans large datasets
- Offer to save useful queries to `_shared-resources\references\` for reuse
