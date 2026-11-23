Tools: read_file(path) reads a file; write_file(path, content) overwrites a file with its full new content; run_shell(cmd) runs a shell command in the working directory.


Running ad-hoc checks: if you run Python in isolated mode (`python3 -I`) or from a different directory, the working directory is NOT on the import path. In the very first check command, either add `import sys; sys.path.insert(0, '.')` before importing local modules, or load the module from its file path. If a check fails with an import or setup error, fix the setup. Don't count it as a result about the code.
