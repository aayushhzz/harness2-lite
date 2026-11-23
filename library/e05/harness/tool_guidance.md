Tools: read_file(path) reads a file; write_file(path, content) overwrites a file with its full new content; run_shell(cmd) runs a shell command in the working directory.


Running ad-hoc Python checks against repo modules: `python3 -I` (isolated mode) leaves the current directory off sys.path, so a plain `from <local_module> import ...` fails. If you use `-I`, start the script with `import sys; sys.path.insert(0, '.')` before any local import. Get the command right the first time. Do not run a check, watch it fail on import, and retry. Keep `-I` for scripts that read untrusted downloaded data. The repository's own code can be imported normally from the working directory.
