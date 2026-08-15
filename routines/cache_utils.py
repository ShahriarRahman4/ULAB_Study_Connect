from django.core.cache import cache


def routine_exams_cache_key(routine_id: int) -> str:
    return f"routine_exams:{routine_id}"


def invalidate_routine_cache(routine_id: int) -> None:
    cache.delete(routine_exams_cache_key(routine_id))
