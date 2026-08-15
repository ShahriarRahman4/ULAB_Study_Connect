from collections import defaultdict
from datetime import date, timedelta
from typing import Iterable


def _days_until(exam_d: date, day: date) -> int:
    return max(1, (exam_d - day).days + 1)


def build_study_plan(
    subjects: Iterable[dict],
    hours_per_day: float,
    start_date: date | None = None,
) -> tuple[dict[date, list[tuple[str, float]]], list[str]]:
    items = []
    for row in subjects:
        code = row.get("course_code") or "?"
        exam_date = row["exam_date"]
        diff = int(row.get("difficulty") or 3)
        diff = max(1, min(5, diff))
        items.append({"course_code": code, "exam_date": exam_date, "difficulty": diff})

    if not items:
        return {}, ["No subjects provided."]

    if start_date is None:
        start_date = date.today()

    last_exam = max(i["exam_date"] for i in items)
    if last_exam < start_date:
        return {}, ["Exam dates are all before the start date."]

    plan: dict[date, list[tuple[str, float]]] = defaultdict(list)
    logs: list[str] = []

    day = start_date
    while day <= last_exam:
        weights: dict[str, float] = {}
        for it in items:
            if it["exam_date"] < day:
                continue
            urgency = 1.0 / _days_until(it["exam_date"], day)
            diff_w = 0.6 + 0.1 * it["difficulty"]
            weights[it["course_code"]] = max(
                weights.get(it["course_code"], 0.0),
                urgency * diff_w,
            )

        total_w = sum(weights.values())
        if total_w <= 0:
            day += timedelta(days=1)
            continue

        for code, w in sorted(weights.items(), key=lambda x: -x[1]):
            share = w / total_w
            hrs = round(hours_per_day * share, 2)
            if hrs > 0:
                plan[day].append((code, hrs))

        day_total = sum(h for _, h in plan[day])
        if day_total and abs(day_total - hours_per_day) > 0.05:
            idx = max(range(len(plan[day])), key=lambda i: plan[day][i][1])
            code, h = plan[day][idx]
            plan[day][idx] = (code, round(h + (hours_per_day - day_total), 2))

        day += timedelta(days=1)

    logs.append(
        f"Planned from {start_date} through {last_exam} at {hours_per_day} h/day."
    )
    return dict(plan), logs


def exams_to_subjects(exam_qs, default_difficulty: int = 3) -> list[dict]:
    out = []
    for ex in exam_qs:
        diff = default_difficulty
        if ex.course_id:
            diff = ex.course.difficulty
        out.append(
            {
                "course_code": ex.course_code,
                "exam_date": ex.exam_date,
                "difficulty": diff,
            }
        )
    return out
