path = "backend/app/adapters/daywise_parser.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Normalize line endings for replacement
is_crlf = "\r\n" in content
content = content.replace("\r\n", "\n")

old_map = """NAME_TO_CODE_MAP: dict[str, str] = {
    # Semester 5 verified course name aliases
    "PROFESSIONAL COMPETANCY ENHANCEMENT": "CDO331",
    "COMPUTER ARCHITECTURE & ORGANISATION LAB": "CSH311C",
    "COMPUTER ARCHITECTURE & ORGANISATION": "CSH301C",
    "OPERATING SYSTEMS LAB": "CSH303C",
    "OPERATING SYSTEMS": "CSH302C",
    "ADVANCED JAVA LAB": "CSH305C",
    "ADVANCED JAVA": "CSH304C",
    "COMPUTER VISION & IMAGE PROCESSING LAB": "CSH319C",
    "COMPUTER VISION & IMAGE PROCESSING": "CSH318C",
    "INTRODUCTION TO NOSQL DATABASES LAB": "CSH312C",
    "INTRODUCTION TO NOSQL DATABASES": "CSH310C",
    "ESSENCE OF INDIAN TRADITIONAL KNOWLEDGE": "EDS240C",
    "RESEARCH & INNOVATION": "RDO202C",
    "INTERDISCIPLINARY PROJECT": "RDO301C",
    "TECHNICAL INTERNSHIP": "RDO204C",
    # Semester 4 verified course name aliases
    "PROFESSIONAL COMPETENCY ENHANCEMENT-II": "CDO232",
    "SOFTWARE ENGINEERING": "CSH213C",
    "SOFTWARE ENGINEERING LAB": "CSH214C",
    "COMPUTER NETWORKS": "CSH215C",
    "COMPUTER NETWORKS LAB": "CSH216C",
    "MACHINE LEARNING": "CSH217C",
    "MACHINE LEARNING LAB": "CSH218C",
    "ADVANCED NEURAL NETWORKS": "CSH219C",
    "ADVANCED NEURAL NETWORKS LAB": "CSH220C",
    "MOBILE APP DEVELOPMENT": "CSW218C",
    "DIGITAL ELECTRONICS": "ECH108C",
    "DIGITAL ELECTRONICS LAB": "ECH109C",
    "INDIAN CONSTITUTION": "LWS101C",
    "ENTREPRENEURSHIP": "MCS368C",
    "DESIGN THINKING": "RDO203C",
    "SPECIALIZED AI ASSOCIATE TRAINING": "VAC-CS512",
}"""

new_map = """NAME_TO_CODE_MAP: dict[str, str] = {
    # Semester 5 verified course name aliases
    "PROFESSIONAL COMPETANCY ENHANCEMENT": "CDO331",
    "COMPUTER ARCHITECTURE & ORGANISATION LAB": "CSH311C",
    "COMPUTER ARCHITECTURE & ORGANISATION": "CSH301C",
    "OPERATING SYSTEMS LAB": "CSH303C",
    "OPERATING SYSTEMS": "CSH302C",
    "ADVANCED JAVA LAB": "CSH305C",
    "ADVANCED JAVA": "CSH304C",
    "COMPUTER VISION & IMAGE PROCESSING LAB": "CSH319C",
    "COMPUTER VISION & IMAGE PROCESSING": "CSH318C",
    "INTRODUCTION TO NOSQL DATABASES LAB": "CSH312C",
    "INTRODUCTION TO NOSQL DATABASES": "CSH310C",
    "ESSENCE OF INDIAN TRADITIONAL KNOWLEDGE": "EDS240C",
    "RESEARCH & INNOVATION": "RDO202C",
    "INTERDISCIPLINARY PROJECT": "RDO301C",
    "TECHNICAL INTERNSHIP": "RDO204C",
    # Semester 4 verified course name aliases
    "PROFESSIONAL COMPETENCY ENHANCEMENT-II": "CDO232",
    "SOFTWARE ENGINEERING": "CSH213C",
    "SOFTWARE ENGINEERING LAB": "CSH214C",
    "COMPUTER NETWORKS": "CSH215C",
    "COMPUTER NETWORKS LAB": "CSH216C",
    "MACHINE LEARNING": "CSH217C",
    "MACHINE LEARNING LAB": "CSH218C",
    "ADVANCED NEURAL NETWORKS": "CSH219C",
    "ADVANCED NEURAL NETWORKS LAB": "CSH220C",
    "MOBILE APP DEVELOPMENT": "CSW218C",
    "DIGITAL ELECTRONICS": "ECH108C",
    "DIGITAL ELECTRONICS LAB": "ECH109C",
    "INDIAN CONSTITUTION": "LWS101C",
    "ENTREPRENEURSHIP": "MCS368C",
    "DESIGN THINKING": "RDO203C",
    "SPECIALIZED AI ASSOCIATE TRAINING": "VAC-CS512",
    # Semester 3 verified course name aliases
    "PROFESSIONAL COMPETANCY ENHANCEMENT-I (PP)": "CDO231",
    "PROFESSIONAL COMPETANCY ENHANCEMENT-I": "CDO231",
    "ANALYSIS & DESIGN OF ALGORITHMS (PP)": "CSH201C",
    "ANALYSIS & DESIGN OF ALGORITHMS": "CSH201C",
    "ANALYSIS & DESIGN OF ALGORITHMS LAB (PR)": "CSH202C",
    "ANALYSIS & DESIGN OF ALGORITHMS LAB": "CSH202C",
    "DATABASE MANAGEMENT SYSTEMS (PP)": "CSH203C",
    "DATABASE MANAGEMENT SYSTEMS": "CSH203C",
    "DATABASE MANAGEMENT SYSTEMS LAB (PR)": "CSH204C",
    "DATABASE MANAGEMENT SYSTEMS LAB": "CSH204C",
    "OOPS USING JAVA (PP)": "CSH205C",
    "OOPS USING JAVA": "CSH205C",
    "OOPS USING JAVA LAB (PR)": "CSH206C",
    "OOPS USING JAVA LAB": "CSH206C",
    "ARTIFICIAL INTELLIGENCE (PP)": "CSH207C",
    "ARTIFICIAL INTELLIGENCE": "CSH207C",
    "ARTIFICIAL INTELLIGENCE LAB (PR)": "CSH208C",
    "ARTIFICIAL INTELLIGENCE LAB": "CSH208C",
    "DISCRETE MATHS (PP)": "MAH204C",
    "DISCRETE MATHS (TUT)": "MAH204C-TUT",
    "WEB DESIGNING-II (PR)": "CSW209C",
    "WEB DESIGNING-II": "CSW209C",
    "ADVANCED PYTHON FOR AI (PP)": "CSS210C",
    "ADVANCED PYTHON FOR AI": "CSS210C",
    "MONGODB JAVA DEVELOPER PATH (PP)": "VAC-CS112",
    "MONGODB JAVA DEVELOPER PATH": "VAC-CS112",
    "UHV II/ SEEK (PP)": "EDN248C",
    "UHV II/ SEEK": "EDN248C",
    "SOCIAL INTERNSHIP-POST 2ND SEM (PP)": "RDO201C",
    "SOCIAL INTERNSHIP-POST 2ND SEM": "RDO201C",
    # Semester 2 verified course name aliases
    "CHEMISTRY-I (PP)": "CHH101C",
    "CHEMISTRY-I": "CHH101C",
    "CHEMISTRY-I LAB (PR)": "CHH102C",
    "CHEMISTRY-I LAB": "CHH102C",
    "CALCULUS & LINEAR ALGEBRA (PP)": "MAH101C",
    "CALCULUS & LINEAR ALGEBRA (TUT)": "MAH101C-TUT",
    "PROFESSIONAL ENGLISH (PP)": "HLS101C",
    "PROFESSIONAL ENGLISH LAB (PR)": "HLS101C-PR",
    "FUNDAMENTALS OF ELECTRONICS & ELECTRICAL ENGINEERING (PP)": "ECH103C",
    "FUNDAMENTALS OF ELECTRONICS & ELECTRICAL ENGINEERING": "ECH103C",
    "FUNDAMENTALS OF ELECTRONICS & ELECTRICAL ENGINEERING LAB (PR)": "ECH104C",
    "FUNDAMENTALS OF ELECTRONICS & ELECTRICAL ENGINEERING LAB": "ECH104C",
    "DATA STRUCTURES (PP)": "CSH107C",
    "DATA STRUCTURES (TUT)": "CSH107C-TUT",
    "DATA STRUCTURES LAB (PR)": "CSH108C",
    "DATA STRUCTURES LAB": "CSH108C",
    "PYTHON PROGRAMMING (PP)": "CSH109C",
    "PYTHON PROGRAMMING": "CSH109C",
    "PYTHON PROGRAMMING LAB (PR)": "CSH110C",
    "PYTHON PROGRAMMING LAB": "CSH110C",
    "PROFESSIONAL COMMUNICATION-II (PP)": "CDO104B",
    "PROFESSIONAL COMMUNICATION-II": "CDO104B",
    "DATA VISUALIZATION (PP)": "CSS112C",
    "DATA VISUALIZATION": "CSS112C",
    "DATA ANALYTICS USING EXCEL (PP)": "VAC-CS109",
    "DATA ANALYTICS USING EXCEL": "VAC-CS109",
    # Semester 1 verified course name aliases
    "PROFESSIONAL COMMUNICATION-I (PP)": "CDO103B",
    "PROFESSIONAL COMMUNICATION-I": "CDO103B",
    "PROGRAMMING FOR PROBLEM SOLVING USING C (PP)": "CSH101C",
    "PROGRAMMING FOR PROBLEM SOLVING USING C": "CSH101C",
    "PROGRAMMING FOR PROBLEM SOLVING USING C LAB (PR)": "CSH102C",
    "PROGRAMMING FOR PROBLEM SOLVING USING C LAB": "CSH102C",
    "ENVIRONMENTAL SCIENCE (PP)": "CHS103C",
    "ENVIRONMENTAL SCIENCE": "CHS103C",
    "QUANTUM MECHANICS FOR ENGINEERS (PP)": "PHH101C",
    "QUANTUM MECHANICS FOR ENGINEERS": "PHH101C",
    "QUANTUM MECHANICS FOR ENGINEERS LAB (PR)": "PHH102C",
    "QUANTUM MECHANICS FOR ENGINEERS LAB": "PHH102C",
    "WEB DESIGNING-I (PR)": "CSW103C",
    "WEB DESIGNING-I": "CSW103C",
    "DATA MODELLING (PP)": "CSS104C",
    "DATA MODELLING LAB (PR)": "CSS104C-PR",
    "COMPUTER AIDED DRAFTING (PR)": "MEW104C",
    "COMPUTER AIDED DRAFTING": "MEW104C",
    "PROBABILITY & STATISTICS (PP)": "MAH104C",
    "PROBABILITY & STATISTICS (TUT)": "MAH104C-TUT",
}"""

old_parse = """        # Extract course code (e.g. CSH301C) or label from subjectName div
        code_match = re.search(r"\\b([A-Z]{2,4}\\d{3}[A-Z]?)\\b", cell_text)
        course_label = code_match.group(1) if code_match else None

        if not course_label:
            subj_div = cell.find("div", class_=re.compile("subjectName", re.I)) or cell.find("div")
            if subj_div:
                subj_text = subj_div.get_text().strip()
                if subj_text:
                    # Clean up (PP)/(PR) and try map to known code
                    norm_name = re.sub(r"\\s*\\((?:PP|PR|TH|IA)\\)\\s*", "", subj_text, flags=re.I).strip().upper()
                    if norm_name in NAME_TO_CODE_MAP:
                        course_label = NAME_TO_CODE_MAP[norm_name]
                    else:
                        course_label = subj_text

        confidence = 1.0 if course_label and re.match(r"^[A-Z]{2,4}\\d{3}[A-Z]?$", course_label) else (0.8 if course_label else 0.0)"""

new_parse = """        # Extract course code (e.g. CSH301C) or label from subjectName div
        code_match = re.search(r"\\b([A-Z]{2,4}\\d{3}[A-Z]?|VAC-[A-Z0-9]+)\\b", cell_text)
        course_label = code_match.group(1) if code_match else None

        if not course_label:
            subj_div = cell.find("div", class_=re.compile("subjectName", re.I)) or cell.find("div")
            if subj_div:
                subj_text = subj_div.get_text().strip()
                if subj_text:
                    raw_subj = subj_text.strip().upper()
                    norm_name = re.sub(r"\\s*\\((?:PP|PR|TH|IA|TUT)\\)\\s*", "", subj_text, flags=re.I).strip().upper()
                    if raw_subj in NAME_TO_CODE_MAP:
                        course_label = NAME_TO_CODE_MAP[raw_subj]
                    elif norm_name in NAME_TO_CODE_MAP:
                        course_label = NAME_TO_CODE_MAP[norm_name]
                    else:
                        course_label = subj_text

        confidence = 1.0 if course_label and re.match(r"^[A-Z0-9\\-]+$", course_label) else (0.8 if course_label else 0.0)"""

assert old_map in content, "old_map not found"
content = content.replace(old_map, new_map, 1)

assert old_parse in content, "old_parse not found"
content = content.replace(old_parse, new_parse, 1)

if is_crlf:
    content = content.replace("\n", "\r\n")

with open(path, "w", encoding="utf-8", newline="") as f:
    f.write(content)
print("Successfully patched daywise_parser.py")
