# Phase 10a — Team Schema

> State: Implemented
> WP: WP-M4-A

## Goal

Parse `configs/teams/*.yaml` team definitions: members + ordered pipeline steps.

## YAML shape

```yaml
meta:
  name: research_report
team:
  members:
    - id: researcher
      agent: web_researcher.yaml
    - id: writer
      agent: general_assistant.yaml
  pipeline:
    - member: researcher
      task: "{team_task}"
    - member: writer
      task: "Write a report from:\n{last_output}"
```

Placeholders: `{team_task}`, `{last_output}`.

## Validation

- Unique member ids
- Pipeline members must exist
- Non-empty task templates
