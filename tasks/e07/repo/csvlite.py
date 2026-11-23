def parse_line(line):
    return [p.strip('"') for p in line.split(",")]
