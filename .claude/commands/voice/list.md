Run this command to list available voices for the current TTS provider:

```bash
python "$CLAUDE_PROJECT_DIR/commands/voice_list.py" "$ARGUMENTS"
```

Print the full table output to the user. If the provider is ElevenLabs and no arguments were given, note that `/voice list all` shows all voices including user-created ones.
