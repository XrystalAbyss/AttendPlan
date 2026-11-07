path = "backend/app/adapters/live_portal_extractor.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

target = """        course_map = {course.code: course for course in snapshot.courses}
        if len(course_map) != len(snapshot.courses):
            report.is_valid = False
            report.quarantined = True
            report.quarantine_reason = "DUPLICATE_COURSE_CODES"
            return report
        matches = []
        parser = ERPAttendanceParser()
        for table in soup.find_all("table"):
            columns = parser._inspect_table_headers(table)
            if "course_code" not in columns or "percent" not in columns:
                continue
            rows = []
            for row in table.find_all("tr"):
                cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
                if len(cells) > max(columns["course_code"], columns["percent"]):
                    course = course_map.get(cells[columns["course_code"]])
                    if course is not None:
                        rows.append((course, cells[columns["percent"]]))
            if rows:
                matches.append(rows)"""

replacement = """        course_map = {course.code: course for course in snapshot.courses}
        if len(course_map) != len(snapshot.courses):
            report.is_valid = False
            report.quarantined = True
            report.quarantine_reason = "DUPLICATE_COURSE_CODES"
            return report
        matches = []
        parser = ERPAttendanceParser()
        for table in soup.find_all("table"):
            columns = parser._inspect_table_headers(table)
            if "course_code" not in columns or "percent" not in columns:
                continue
            rows = []
            course_idx = 0
            for row in table.find_all("tr"):
                cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
                if any(cell.name == "th" for cell in row.find_all(["td", "th"])):
                    continue
                row_text = row.get_text().lower()
                if "total" in row_text or "grand total" in row_text or "total percentage" in row_text:
                    continue
                if len(cells) > max(columns["course_code"], columns["percent"]):
                    c_code = cells[columns["course_code"]]
                    if c_code and course_idx < len(snapshot.courses):
                        course = snapshot.courses[course_idx]
                        if course.code.startswith(c_code):
                            rows.append((course, cells[columns["percent"]]))
                            course_idx += 1
            if rows:
                matches.append(rows)"""

assert target in content, "Target not found in content"
new_content = content.replace(target, replacement, 1)
with open(path, "w", encoding="utf-8", newline="") as f:
    f.write(new_content)
print("Successfully updated live_portal_extractor.py")

