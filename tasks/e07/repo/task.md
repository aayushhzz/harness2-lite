Symptom: the contacts importer splits "Smith, John" into two columns, and a note field containing quotes is imported with stray double quotes around it.

Function contract: `parse_line(line)` in `csvlite.py` returns the list of fields of one CSV line. Fields are separated by commas that are outside double quotes. Surrounding double quotes are removed. Inside a quoted field, two double quotes in a row stand for one literal double quote. An empty line gives a list with one empty field. A trailing comma gives a final empty field.

There are no tests in this repository. Verify your fix yourself.
