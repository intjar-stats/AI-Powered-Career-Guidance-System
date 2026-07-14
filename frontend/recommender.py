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


def get_skill_gap(target_career):

    data = career_skill_gap[
        career_skill_gap["Target_Career"] == target_career
    ]

    if data.empty:
        return None

    row = data.iloc[0]

    return {
        "current": row["Current_Skills"],
        "required": row["Required_Skills"],
        "gap": row["Gap_Percentage"],
        "hours": row["Estimated_Hours"],
        "courses": row["Recommended_Courses"],
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