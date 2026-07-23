from data_loader import load_data

(
    career_prediction,
    career_recommendation,
    career_learning_path,
    career_skill_gap,
) = load_data()


def recommend_career(age, gender, degree_level):
    filtered = career_recommendation.copy()
    # Gender Filter
    filtered = filtered[
        filtered["gender"].str.lower() == gender.lower()
    ]
    # Degree Filter
    filtered = filtered[
        filtered["degree_level"].str.lower() == degree_level.lower()
    ]
    if filtered.empty:
        filtered = career_recommendation
    row = filtered.iloc[0]
    return {
        "career1": row["recommended_job_1"],
        "career2": row["recommended_job_2"],
        "career3": row["recommended_job_3"],
    }


# --- Skill gap (personalized, based on the student's own profile ratings) ---
# Replaces the old get_skill_gap(target_career), which returned a fixed CSV
# row (same Gap_Percentage and Estimated_Hours for every student who got the
# same recommended career, regardless of their actual skills). That is why
# the app was always showing a 48% gap and fixed hour estimates for everyone.

SKILL_NAME_TO_PROFILE_KEY = {
    "python": "python",
    "java": "java",
    "c/c++": "c_cpp",
    "c++": "c_cpp",
    "sql": "sql",
    "machine learning": "machine_learning",
    "data analysis": "data_analysis",
    "cloud computing": "cloud_computing",
    "cybersecurity": "cybersecurity",
    "web development": "web_development",
    "devops": "devops",
    "networking": "networking",
    "communication": "communication",
    "leadership": "leadership",
    "problem solving": "problem_solving",
    "teamwork": "teamwork",
    "adaptability": "adaptability",
}

READY_THRESHOLD = 3
HOURS_PER_LEVEL = 15
DEFAULT_RATING_IF_UNMAPPED = 1


def _get_required_skills(target_career):
    data = career_skill_gap[career_skill_gap["Target_Career"] == target_career]
    if data.empty:
        return None
    return [s.strip() for s in data.iloc[0]["Required_Skills"].split(",")]


def _get_recommended_courses(target_career):
    data = career_skill_gap[career_skill_gap["Target_Career"] == target_career]
    if data.empty:
        return None
    return data.iloc[0]["Recommended_Courses"]


def compute_skill_gap(profile, target_career):
    """
    Personalized skill gap based on the student's own slider ratings.
    Replaces the old get_skill_gap(), which returned a fixed CSV row
    regardless of the student's actual profile.
    """
    required_skills = _get_required_skills(target_career)
    if required_skills is None:
        return None

    ready_skills = []
    gap_skills = []
    total_hours = 0

    for skill in required_skills:
        key = SKILL_NAME_TO_PROFILE_KEY.get(skill.strip().lower())
        rating = profile.get(key, DEFAULT_RATING_IF_UNMAPPED) if key else DEFAULT_RATING_IF_UNMAPPED

        if rating >= READY_THRESHOLD:
            ready_skills.append(skill)
        else:
            gap_skills.append(skill)
            total_hours += (READY_THRESHOLD - rating) * HOURS_PER_LEVEL

    total_required = len(required_skills)
    gap_percentage = round((len(gap_skills) / total_required) * 100, 1) if total_required else 0.0

    return {
        "current": ", ".join(ready_skills) if ready_skills else "None yet",
        "required": ", ".join(required_skills),
        "gap": gap_percentage,
        "hours": total_hours,
        "courses": _get_recommended_courses(target_career) or "N/A",
    }


def get_learning_path(target_career):
    data = career_learning_path[
        career_learning_path["Target_Career"] == target_career
    ]
    if data.empty:
        return None
    row = data.iloc[0]
    return {
        "stage": row["Learning_Stage"],
        "skills": row["Priority_Skills"],
        "path": row["Learning_Path"],
        "resources": row["Recommended_Resources"],
        "duration": row["Estimated_Duration"],
        "milestone": row["Milestone"],
    }
