def remove_comments(assembly):
    commentless = []
    for line in assembly:
        try:
            line = line[: line.index(";")]
        except:
            line = line
        commentless.append(line)

    return commentless


def collect_labels(assembly):
    # make note of the symbols and register names
    symbols = {}
    pc = 0
    for line in assembly:

        fields = line.strip().split()

        if not fields:
            continue  # empty line
        if line[0] > " ":
            symbol = fields[0]
            if symbol[0] != ".":
                symbols[
                    symbol[:-1]
                ] = pc  # remove the colon and save the memory address
        else:
            pc = pc + 1
    return symbols


def resolve_labels(assembly, symbols):
    final = []
    for line in assembly:
        fields = line.split()
        if not fields:
            continue  # skip empty lines
        if len(fields) == 1:
            continue  # drop just the labels
        line = line.strip()  # remove whitespace

        final.append(line)
    return final


def assemble(assembly):

    assembly = remove_comments(assembly)
    symbols = collect_labels(assembly)
    prog = resolve_labels(assembly, symbols)

    return prog, symbols
