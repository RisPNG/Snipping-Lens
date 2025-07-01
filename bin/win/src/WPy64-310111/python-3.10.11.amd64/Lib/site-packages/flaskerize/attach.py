from flaskerize.utils import split_file_factory


def attach(args):

    print("Attaching...")
    # TODO: Check that the provided blueprint exists, error if not
    filename, func = split_file_factory(args.to)
    key_lines, contents = _find_key_lines(filename, func)

    # TODO: remove the need for this check by enabling an existing static dir (see #3)
    # (https://github.com/apryor6/flaskerize/issues/3)
    indent = " " * 4  # TODO: dynamically determine indentation
    new_static = ", static_folder=None"

    # TODO: Verify that the flask line is greater than start_func or, more rigorously,
    # make sure that you are inserting from back to front so that the line numbers are
    # not perturbed as you go
    call_to_Flask = [c.strip() for c in contents[key_lines["flask"]][:-1].split(",")]

    # TODO: Clean up this messy logic that is simply checking if the static_folder you
    # want to add is already present
    # TODO: Support multi-line definitions where the Flask call is not only one line
    if not any("static_folder" in c for c in call_to_Flask):
        updated = (
            ", ".join(i.strip() for i in call_to_Flask if "static_folder" not in i)
            + new_static
        )

        if updated.strip() != ", ".join(call_to_Flask).strip():
            contents[key_lines["flask"]] = f"{indent}{updated})"
    register_line = f"{indent}app.register_blueprint(site, url_prefix='/')"
    if (
        register_line not in contents
        and register_line.replace("'", '"') not in contents
    ):
        contents.insert(key_lines["flask"] + 1, register_line)

    import_bp_line = f"{indent}from {args.bp.replace('.py', '')} import site"
    if import_bp_line not in contents:
        contents.insert(key_lines["start_func"] + 1, import_bp_line)

    contents = "\n".join(contents)
    if args.dry_run:
        print("Dry run result: ")
        print(contents)
    else:
        with open(filename, "w") as fid:
            fid.write(contents)


def _find_key_lines(filename: str, func):
    TOKEN_START_FUNC = f"def {func}"
    TOKEN_FLASK = "Flask("
    key_lines = {}
    with open(filename, "r") as fid:
        for num, line in enumerate(fid):
            if is_comment(line):  # ignore comments
                continue
            if TOKEN_START_FUNC in line:
                key_lines["start_func"] = num
            if TOKEN_FLASK in line:
                key_lines["flask"] = num
    if not key_lines.get("start_func", None):
        raise SyntaxError(
            f"The provided factory '{func}' was not found in file '{filename}'"
        )
    if not key_lines.get("flask", None):
        raise SyntaxError(
            f"No call to Flask was found in the provided file '{filename}'."
            "Is your app factory setup correctly?"
        )
    with open(filename, "r") as fid:
        contents = fid.read().splitlines()
    return key_lines, contents


def is_comment(line: str) -> bool:
    return line.strip().startswith("#")
