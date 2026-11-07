path = "backend/app/adapters/portal_safety.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

is_crlf = "\r\n" in content
content = content.replace("\r\n", "\n")

old_def = """def validate_result(result: Any, year: str, semester: int, class_id: str, class_label: str, month: str | None = None, require_dates: bool = False) -> None:"""

new_def = """def validate_result(
    result: Any,
    year: str | None = None,
    semester: int | None = None,
    class_id: str | None = None,
    class_label: str | None = None,
    month: str | None = None,
    require_dates: bool = False,
    **kwargs: Any,
) -> None:
    if year is None:
        year = kwargs.get("academic_year")
    if semester is None:
        semester = kwargs.get("semester")
    if class_id is None:
        class_id = kwargs.get("class_id")
    if class_label is None:
        class_label = kwargs.get("class_label")"""

assert old_def in content, "old_def not found"
content = content.replace(old_def, new_def, 1)

if is_crlf:
    content = content.replace("\n", "\r\n")

with open(path, "w", encoding="utf-8", newline="") as f:
    f.write(content)
print("Successfully updated portal_safety.py")

