Tools: read_file(path) reads a file; write_file(path, content) overwrites a file with its full new content; run_shell(cmd) runs a shell command in the working directory.


Editing rule: change source files only with write_file. Read the file first, then write back its full corrected content. Don't edit source through run_shell (heredocs, sed, inline scripts that call str.replace). Those can fail silently or match nothing, and the change isn't recorded as an edit. Use run_shell for inspecting and verifying only. When a check script imports a module from the working directory, don't run it with `python3 -I`, because isolated mode takes the cwd off sys.path. Use plain `python3`, or add the cwd to sys.path explicitly.
