Tools: read_file(path) reads a file; write_file(path, content) overwrites a file with its full new content; run_shell(cmd) runs a shell command in the working directory.

When running ad-hoc Python checks that import modules from the working directory: `python3 -I` removes the cwd from sys.path, so a plain import fails. Either use plain `python3`, or put `import sys; sys.path.insert(0, '<absolute workspace path>')` before the import on the first attempt. Print one labeled line per contract clause with input, expected, actual, and PASS/FAIL, and read every line before you move on.
