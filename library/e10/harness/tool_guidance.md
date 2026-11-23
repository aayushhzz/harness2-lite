Tools: read_file(path) reads a file; write_file(path, content) overwrites a file with its full new content; run_shell(cmd) runs a shell command in the working directory.


Editing rules:
- Change source files with write_file (read_file first, then write the full corrected content). Do not patch source through shell one-liners, heredocs or regex-replace scripts. They can fail silently or only partly, and they skip edit tracking.
- If any tool call returns a non-zero exit code or an error, assume the file state is unknown. Re-read the affected file with read_file and confirm the intended change is there before you run checks or report success.
- When checking a module from the working directory with an ad-hoc script, make sure the cwd is importable (plain python3, or keep sys.path.insert(0, '.') if you use -I).
