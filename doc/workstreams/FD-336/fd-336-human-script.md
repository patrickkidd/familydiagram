# FD-336 — the embedded chat

- The bet: one writer — the chat drives the same case the canvas shows, and only that case is ever written.
- Judge the shape, not the bug count: whether this foundation holds for what gets built on it.
- Say what you saw, never what you think caused it.
- Harness reference if you want one: `/Users/patrick/theapp/familydiagram/.claude/worktrees/FD-336/doc/SANDBOX.md`
- Branch FD-336 in all three worktrees; PRs https://github.com/patrickkidd/familydiagram/pull/150 and https://github.com/patrickkidd/btcopilot/pull/132. Everything not below is machine-verified.

## The walk

- Bring it up. It prints a url, a database, and which checkout each repo runs from.

```
~/theapp/.claude/worktrees/FD-336/bin/sandbox up FD-336 --seed family+hostile --llm real --pro
```

- If that output says the backend has no credentials, run `set -a; . ~/theapp/.env; set +a` and paste the line above again.
- In Pro, open the case named **Three Generations**.
- Click the chat icon in the case's right drawer — Discuss, Learn and Plan appear beside the canvas.
- In Discuss, type this and press Enter:

```
My aunt Marguerite Halloran raised my cousin Dean Halloran after the funeral.
```

- When the coach has answered, press Extract, then accept what it proposes. Marguerite and Dean should land on the canvas, each with a readable label.
- Press Cmd-S, close the case, reopen Three Generations. Both should still be there, still labelled.

## Optional

- Layout: at your normal window size, nothing in the three tabs should be clipped, every tab should be reachable, and the drawer should widen and narrow cleanly.
- The save prompt: drag a person to a new spot, then send another statement. You should get exactly one prompt to save — judge whether it reads sensibly and whether you would resent it mid-session. Save sends the statement; Cancel does not.
- Quiet when clean: send one more statement with nothing edited. There should be no prompt at all.
- Blank labels, locally: take it down, bring it up on the awkward names, and open the case **Hostile Names** — no person symbol should be blank.

```
~/theapp/.claude/worktrees/FD-336/bin/sandbox down FD-336
~/theapp/.claude/worktrees/FD-336/bin/sandbox up FD-336 --seed hostile+family --llm stub --pro
```

- Blank labels, for real: after release, open diagram 1924 in production and confirm every person symbol carries a label. The local copy-of-production rehearsal (`--seed prod`) cannot run yet — the restored licence names a different machine.
- Finished — take it down:

```
~/theapp/.claude/worktrees/FD-336/bin/sandbox down FD-336
```
