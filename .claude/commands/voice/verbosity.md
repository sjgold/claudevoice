Run this command to set voice verbosity. The level is: $ARGUMENTS

```bash
python "$CLAUDE_PROJECT_DIR/commands/voice_verbosity.py" "$ARGUMENTS"
```

Then invoke the `voice-caveman` skill via the Skill tool with `args: "$ARGUMENTS"` to load the verbosity enforcement rules for the rest of this conversation.

After the skill is loaded, confirm to the user with only these words (nothing else): "Level one." / "Level two." / "Level three." / "Level four." — matching the level set.
