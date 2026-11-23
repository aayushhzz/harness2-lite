Symptom: feature flags set to "false" in the settings file still turn the feature on. The problem shows up in app.py, where `is_enabled` is called for every request, and the flag is never honoured.

Function contract: `parse_bool(s)` in `config.py` turns a settings string into a bool. It ignores case and surrounding whitespace. "true", "1", "yes" and "on" give True. "false", "0", "no", "off" and the empty string give False. Any other text raises ValueError. `is_enabled(settings, key, default=False)` in `app.py` returns `default` when the key is missing. If the value is a string it is parsed with `parse_bool`; any other value is converted with `bool()`.

There are no tests in this repository. Verify your fix yourself.
