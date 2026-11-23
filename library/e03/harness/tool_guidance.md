Tools: read_file(path) reads a file; write_file(path, content) overwrites a file with its full new content; run_shell(cmd) runs a shell command in the working directory.


Checking local code with run_shell: a check script that imports a module from the working directory must be able to find it. `python3 -I` (isolated mode) removes the current directory from sys.path, so a plain `from <module> import ...` will fail. For checks on the repository's own code, either run `python3 -c ...` without `-I`, or put `import sys; sys.path.insert(0, '.')` before the import. Get this right the first time; a failed import tells you nothing about the fix. Keep `-I` for running untrusted downloaded files, not the project you were asked to fix.
