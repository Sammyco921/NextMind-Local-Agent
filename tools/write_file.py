def write_file(filename, content):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "status": "success",
        "file": filename,
        "bytes": len(content)
    }