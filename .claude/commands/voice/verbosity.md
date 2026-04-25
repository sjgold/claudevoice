Run this command to set voice verbosity. The level is: $ARGUMENTS

```bash
python "C:/Users/SJG/Documents/CodePlayground/claude voice/commands/voice_verbosity.py" "$ARGUMENTS"
```

Then, based on the level, immediately adopt the following rule for the rest of this conversation:

**If level is "low":** Max 2 sentences per response. Drop filler words and articles. Use fragments. No bullet lists — if you must list things, inline them as "X, Y, and Z." Pattern: [thing] [action]. Done. No preamble, no summary, no sign-off.

**If level is "medium":** Max 4 sentences. Drop filler. Bullets allowed but max 3 items; if more, note count ("...and 2 more"). No preamble.

**If level is "high":** No special constraints on format or length.

Confirm to the user: "Verbosity set to [level] — taking effect now in this conversation."
