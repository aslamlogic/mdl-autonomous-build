# Meta System

Run:

```bash
python -m meta_system.orchestrator --specs-dir specs/apps/ --apps-dir apps/ --meta-dir meta_system/
```

This orchestrator:
- loads multiple app specs
- builds engines and apps
- deploys apps
- runs tasks in parallel
