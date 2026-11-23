Tools: read_file(path) reads a file; write_file(path, content) overwrites a file with its full new content; run_shell(cmd) runs a shell command in the working directory.


Editing rules:
- Always change source files with write_file(path, content), giving the complete new file content. Never write or rewrite source files from run_shell (heredocs, echo/printf redirection, sed -i). Shell writes can fail on quoting, and they are not tracked as edits.
- After write_file, read_file the same path once to confirm the content is what you intended before running checks.
- Use run_shell only to run commands and checks, not to modify files you are delivering.
- When running a check script that imports a module from the working directory, run it from the working directory and do not use `python3 -I`. Isolated mode drops the current directory from sys.path, so the import fails.
