---
name: reset-plan-review
description: Reset plan-review state for E2E testing
allowed-tools: Bash
---

Reset plan-review state without a full re-initialize. For E2E testing only.

!`python3 -c "
import json, sys
p = '${CLAUDE_PLUGIN_ROOT}/scripts/state.jsonl'
sid = '${CLAUDE_SESSION_ID}'
lines = open(p).read().strip().splitlines()
keep = {'explore', 'research', 'plan', 'plan-review'}
out = []
for line in lines:
    s = json.loads(line)
    if s.get('session_id') == sid:
        s['phases'] = [ph for ph in s['phases'] if ph['name'] in keep]
        for ph in s['phases']:
            if ph['name'] == 'plan-review':
                ph['status'] = 'in_progress'
        s['plan']['reviews'] = []
        s['plan']['revised'] = None
        s['agents'] = [a for a in s.get('agents', []) if a.get('name') != 'PlanReview']
        print('plan-review reset OK', file=sys.stderr)
    out.append(json.dumps(s, separators=(',',':')))
open(p, 'w').write('\n'.join(out) + '\n')
"`
