### Dependency Health Check

These are foundational items that many things depend on — this is normal:

```
TS-012 (Next.js scaffold)  ← 1 story needs this
TS-013 (Firebase setup)    ← 1 story needs this
TS-016 (Python setup)      ← implicitly everything in EP-001
SK-001 (Feature selection) ← 2 stories need this
EP-001 (as a whole)        ← EP-002, EP-003, EP-004 all need its output
```

This is fine. Foundation work fans out. Do it first, everything else unlocks.

### Chain (Problematic)

```
EP-001 chain:
  SK-001 → TS-002 → TS-003 → US-001
  TS-001 ↗ TS-002 (also feeds in)

That's a 4-step chain. US-001 can't start until
three other items complete in sequence.
```

```
EP-003 chain:
  EP-001 + EP-004 → US-004 → US-005 (also needs SK-004)

US-005 needs US-004 which needs two entire epics done first.
```

### Cross-Epic Dependencies (The Real Problem)

| Story  | Needs                 | Problem                                          |
| ------ | --------------------- | ------------------------------------------------ |
| TS-004 | EP-001 output         | EP-002 can't start until EP-001 delivers         |
| US-004 | EP-001 + EP-004 data  | EP-003 can't start until two other epics deliver |
| US-006 | EP-001 pipeline       | EP-004 can't start until EP-001 delivers         |
| TS-008 | EP-001 scripts        | Same                                             |
| US-007 | EP-002 + EP-003 pages | EP-005 can't start until two other epics deliver |

This creates a forced sequence:

```
EP-001 (model) → EP-002 (blog) → EP-005 (ads)
                → EP-003 (dashboard) ↗
                → EP-004 (automation)
```

You can't parallelize epics. Everything waterfalls from EP-001.

### Recommendations

**1. Separate page structure from data.** You're already doing this with TS-005 and TS-006 — building page templates with mock data independently. That's smart. But US-004 and US-005 don't reflect this. They could be split:

```
Current:
  US-004: Public win/loss record → Needs EP-001, EP-004 data

Split into:
  US-004: Public win/loss record with mock data → Independent
  TS-XXX: Connect dashboard to live prediction data → Needs EP-001, EP-004
```

This lets you build and test the full UI before the model exists.

**2. US-005 depending on US-004 is suspicious.** Is ROI tracking truly impossible without the win/loss record? Or can they be built independently and both connect to the same data source? If so:

```
Current:
  US-004 → US-005

Independent:
  US-004: Win/loss record (reads from results store)
  US-005: ROI tracking (reads from results store)
  Both need: TS-009 (results update pipeline)
```

**3. EP-001 chain could be shorter.** TS-002 and TS-003 feel like tasks within one story, not separate stories:

```
Current (3 stories):
  TS-001: Data ingestion
  TS-002: Feature engineering → Needs SK-001, TS-001
  TS-003: Model training → Needs SK-001, TS-002

Could be (2 stories):
  TS-001: Data ingestion
  TS-002: Feature engineering + model training → Needs SK-001, TS-001
```

TS-002 and TS-003 can't deliver user value independently — there's no point having engineered features without a trained model. They're one story with two tasks.

### Summary

| Issue                                        | Severity                                          | Fix                                                                            |
| -------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------ |
| EP-001 is a hard prerequisite for everything | Normal for this domain — the model IS the product | No fix needed, just do it first                                                |
| EP-001 internal chain is 4 steps             | Moderate                                          | Merge TS-002 + TS-003 into one story                                           |
| US-004 → US-005 chain                        | Mild                                              | Make both independent, both read from same data                                |
| Cross-epic dependencies                      | Normal for solo dev                               | Separate UI (mock data) from data integration                                  |
| 64% dependency rate                          | High but explainable                              | Most trace back to EP-001 as foundation — that's structural, not a design flaw |

The backlog isn't badly structured — it reflects a product where the ML model is the core and everything else consumes its output. That's just reality. The improvements are about unlocking UI work earlier with mock data so you're not blocked on the model for _everything_.
