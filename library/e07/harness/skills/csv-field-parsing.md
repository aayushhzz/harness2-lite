# Fixing hand-written CSV/quoted-field parsers

When fixing a function like parse_line(line):
- Write each test input as the RAW line. The bug-report value "Smith, John" only stays one field when it is quoted in the line: '"Smith, John",x' -> ['Smith, John','x']. An unquoted 'Smith, John' SHOULD split into ['Smith', ' John'].
- Use one case per contract clause, each printing input/expected/actual/PASS-FAIL:
  - plain: 'a,b' -> ['a','b']
  - quoted comma: '"Smith, John",x' -> ['Smith, John','x']
  - quotes stripped: '"note"' -> ['note']
  - escaped quote: '"say ""hi"""' -> ['say "hi"']
  - empty line: '' -> ['']
  - trailing comma: 'a,' -> ['a','']
  - empty quoted field: '"",b' -> ['','b']
- Don't trim spaces unless the contract says to.
- Run with plain python3 from the workspace, or add sys.path.insert(0, '<workspace>') if you use -I.
- Any FAIL means you are not done. Check the contract to see whether the code or the expectation is wrong, fix it, and rerun until every line passes.
