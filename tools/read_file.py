def read_file(filename):
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()

    return {
        "status": "success",
        "file": filename,
        "content": content,
        "bytes": len(content)
    }