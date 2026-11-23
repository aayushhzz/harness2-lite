Tools: read_file(path) reads a file; write_file(path, content) overwrites a file with its full new content; run_shell(cmd) runs a shell command in the working directory.


Running your own check scripts: `python3 -I` (isolated mode) removes the current directory from sys.path, so a plain import of a module in the working directory will fail. If you use `-I`, the script's first line must be `import sys; sys.path.insert(0, '.')`, placed before any import of project code. You can also run the check without `-I` when the only code it loads is the repository code you are fixing. Fix this before the first run so you don't waste a step on an import error.
