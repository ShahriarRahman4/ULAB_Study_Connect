from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Iterable

MAX_BLOCKS_PER_DAY = 6


def _days_until(exam_d: date, day: date) -> int:
    return max(1, (exam_d - day).days + 1)


def build_study_plan(
    subjects: Iterable[dict],
    hours_per_day: float,
    start_date: date | None = None,
    end_date: date | None = None,
    review_days: int = 10,
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
    if end_date is None:
        if last_exam >= start_date:
            end_date = last_exam
        else:
            end_date = start_date + timedelta(days=max(1, review_days) - 1)

    if end_date < start_date:
        return {}, ["End date is before start date."]

    logs: list[str] = [
        f"Planned from {start_date} through {end_date} at {hours_per_day} h/day."
    ]

    plan: dict[date, list[tuple[str, float]]] = defaultdict(list)

    day = start_date
    while day <= end_date:
        weights: dict[str, float] = {}
        for it in items:
            if it["exam_date"] < day:
                urgency = 0.4
            else:
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

        ranked = sorted(weights.items(), key=lambda x: -x[1])[:MAX_BLOCKS_PER_DAY]
        ranked_total = sum(w for _, w in ranked) or 1.0
        for code, w in ranked:
            hrs = round(hours_per_day * (w / ranked_total), 2)
            if hrs > 0:
                plan[day].append((code, hrs))

        if plan[day]:
            day_total = sum(h for _, h in plan[day])
            if abs(day_total - hours_per_day) > 0.05:
                idx = max(range(len(plan[day])), key=lambda i: plan[day][i][1])
                code, h = plan[day][idx]
                plan[day][idx] = (code, round(h + (hours_per_day - day_total), 2))

        day += timedelta(days=1)

    return dict(plan), logs
