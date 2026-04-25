Run this command to enable voice TTS:

```bash
python "$CLAUDE_PROJECT_DIR/commands/voice_on.py"
```

Then invoke the `voice-caveman` skill via the Skill tool (no args — it reads the current verbosity from `~/.claude/voice-config.json`).

After the skill is loaded, confirm with only: "Voice on."
