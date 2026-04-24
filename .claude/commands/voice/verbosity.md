Run this command to set voice verbosity. The level is: $ARGUMENTS

```bash
python "C:/Users/SJG/Documents/CodePlayground/claude voice/commands/voice_verbosity.py" "$ARGUMENTS"
```

Then, based on the level, immediately adopt the following rule for the rest of this conversation:

**If level is "low":** Do not use bullet lists. Summarize any list as a single sentence. Example: "There are four considerations: X, Y, Z, and one more."

**If level is "medium":** When using bullet lists, limit to 3 items. If you have more, include the most important 3 and note how many were omitted (e.g. "...and 2 more").

**If level is "high":** No special constraints on format or length.

Confirm to the user: "Verbosity set to [level] — taking effect now in this conversation."
