# Final Report: Draft Section 9 (Career Guidance & Roadmap Generation Module)

> Status: Draft for review. Author: Ritik Gupta (Career Guidance & Roadmap Generation).
> One note: Section 9.6 generalizes the personal reason Ritik gave for a scope
> change, out of respect for privacy. He can confirm the wording is acceptable,
> or provide different phrasing if preferred.

---

## 9. Career Guidance and Roadmap Generation Module

### 9.1 Overview

This module covers two components of the pipeline that run immediately after the machine learning prediction step and before the Generative AI explanation step: Skill Gap Analysis and Learning Roadmap generation, along with validating that both behave correctly across different student profiles.

Work on this module began with studying the ML module's inputs, outputs, and overall data flow, to understand exactly how a student profile becomes a ranked career recommendation, before taking direct ownership of the downstream skill-gap and roadmap logic.

### 9.2 Module Scope and Responsibilities

Per the team's role and responsibility matrix, this module covers:

- Designing the career guidance logic that consumes the ML model's top prediction.
- Generating skill-gap explanations personalized to the student's own inputs.
- Generating learning roadmaps mapped to the recommended career.
- Validating that recommendations behave correctly across different student profiles.

### 9.3 System Flow: Profile to Career to Skills to Roadmap

A student fills in their profile (degree, GPA, experience) and rates 16 technical and soft skills from 1 to 5. This profile is passed to the ML Recommendation Engine (Section 7), which returns the Top-3 predicted careers ranked by confidence. The top-ranked career is then handed to the skill-gap and roadmap logic:

- **Skill Gap Analysis:** the fixed list of skills required for the predicted career is retrieved from the reference dataset. Each required skill is checked against the student's own self-rated level for that skill. A skill counts as a current strength if the student's rating meets a minimum "ready" level; otherwise it counts as a gap, contributing a proportional number of estimated learning hours based on how far below that level the student's rating sits. Summing across all required skills produces the student's own gap percentage and estimated hours.
- **Learning Roadmap Generation:** for the same predicted career, the matching learning stage, priority skills, ordered learning path, recommended resources, estimated duration, and milestone are retrieved and assembled into a single roadmap block, giving the student a clear sequence of what to learn next and in what order.

### 9.4 Data Sources

Both modules draw from two reference datasets, each containing one row per career category (approximately 1,000 rows spanning 13 career categories in each file).

**`career_skill_gap.csv`**

| Column | Represents |
|---|---|
| Target_Career | The career label this row applies to, matched against the ML model's top prediction. |
| Current_Skills | A reference baseline skill set (used as a fallback reference, not the student's own input). |
| Required_Skills | The fixed list of skills expected for this career, the basis for the gap comparison. |
| Gap_Percentage | Original static reference value, now superseded per-student by the computed gap (Section 9.5). |
| Estimated_Hours | Original static reference value, likewise superseded by the computed figure. |
| Recommended_Courses | Course suggestions tied to the required-skill list, used as-is. |

**`career_learning_path.csv`**

| Column | Represents |
|---|---|
| Target_Career | The career label this row applies to, matched against the ML model's top prediction. |
| Learning_Stage | A Beginner / Intermediate / Advanced classification for the roadmap. |
| Priority_Skills | The skills to focus on first for this career. |
| Learning_Path | An ordered sequence describing the recommended learning order. |
| Resources | Suggested courses or materials for the roadmap. |
| Estimated_Duration | Expected time to complete the roadmap. |
| Milestone | The target outcome once the roadmap is completed. |

### 9.5 Personalizing the Skill Gap Calculation

During validation, the Skill Gap Analysis was found to return the identical gap percentage and estimated hours for every student who received the same top career recommendation, regardless of their individual skill ratings. The root cause was that the original lookup function always read the first matching row for that career from `career_skill_gap.csv`, rather than referencing the student's own submitted profile.

This was resolved by rewriting the function as `compute_skill_gap(profile, target_career)`, which reads the required-skills list for the career from the dataset and compares it individually against each student's own slider ratings, computing the gap percentage and estimated hours per student rather than reusing a stored value.

This was verified on the live deployed application: two profiles predicted the same top career but with different skill ratings produced different, profile-specific results, in place of the previous fixed result shown to everyone regardless of their profile. This is recorded as DEF-07 in the project's defect log (`tests/Testing_Plan.md`).

### 9.6 Note on Roadmap Generation Module Scope

The originally proposed rule-based `roadmap_generation` module could not be completed within the assigned development window due to an unforeseen personal emergency. To meet the submission deadline, the team adopted the existing CSV-based lookup described in Section 9.3 as an interim substitute. Following Ritik's return, the corresponding logic, including the skill gap personalization fix documented in Section 9.5, was completed and verified.

### 9.7 Conclusion

The Skill Gap Analysis and Learning Roadmap components together give students a personalized bridge between their predicted career and the skills required to reach it, computed directly from their own profile rather than a generic, static reference. The fix documented in Section 9.5 closed a major defect identified during testing.
