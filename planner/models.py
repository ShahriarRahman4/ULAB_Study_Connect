from datetime import timedelta, date
from collections import defaultdict

from django.db import models
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count

User = get_user_model()


class StudyPlan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='study_plans')
    routine = models.ForeignKey('routines.SavedRoutine', on_delete=models.SET_NULL, null=True, blank=True, related_name='study_plans')
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def start_date(self):
        first_task = DailyTask.objects.filter(course_plan__plan=self).order_by('date').first()
        return first_task.date if first_task else None

    @property
    def end_date(self):
        last_task = DailyTask.objects.filter(course_plan__plan=self).order_by('-date').first()
        return last_task.date if last_task else None

    @property
    def total_tasks(self):
        return DailyTask.objects.filter(course_plan__plan=self).count()

    @property
    def completed_tasks(self):
        return DailyTask.objects.filter(course_plan__plan=self, is_completed=True).count()

    @property
    def remaining_tasks(self):
        return self.total_tasks - self.completed_tasks

    @property
    def total_progress(self):
        if self.total_tasks == 0:
            return 0.0
        return round((self.completed_tasks / self.total_tasks) * 100, 1)

    @property
    def completed_tasks_percentage(self):
        return self.total_progress

    @property
    def tasks_by_date(self):
        tasks = DailyTask.objects.filter(course_plan__plan=self).select_related('course_plan')
        grouped = defaultdict(list)
        for task in tasks:
            grouped[task.date].append(task)
        return dict(sorted(grouped.items()))

    @property
    def nearest_exam_date(self):
        exams = []
        for cp in self.course_plans.all():
            exam_date = cp._get_exam_date()
            if exam_date:
                exams.append(exam_date)
        if not exams:
            return None
        today = date.today()
        future_exams = [e for e in exams if e >= today]
        if future_exams:
            return min(future_exams)
        return max(exams)

    @property
    def nearest_exam_days(self):
        exam_date = self.nearest_exam_date
        if not exam_date:
            return None
        return (exam_date - date.today()).days

    @property
    def days_left_percentage(self):
        start = self.start_date
        end = self.end_date
        if not start or not end:
            return 0.0
        today = date.today()
        total_days = (end - start).days
        if total_days <= 0:
            return 100.0
        days_passed = max(0, (today - start).days)
        return round(min(100.0, (days_passed / total_days) * 100), 1)


class CoursePlan(models.Model):
    RATING_WEAK = 'weak'
    RATING_MEDIUM = 'medium'
    RATING_HARD = 'hard'

    RATING_CHOICES = [
        (RATING_WEAK, 'Weak'),
        (RATING_MEDIUM, 'Medium'),
        (RATING_HARD, 'Hard'),
    ]

    plan = models.ForeignKey(StudyPlan, on_delete=models.CASCADE, related_name='course_plans')
    course_code = models.CharField(max_length=50)
    rating = models.CharField(max_length=10, choices=RATING_CHOICES, default=RATING_MEDIUM)
    progress_percentage = models.FloatField(default=0.0)
    is_completed = models.BooleanField(default=False)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.course_code} - {self.plan.name}"

    def _get_exam_date(self):
        if self.plan.routine is None:
            return None
        try:
            exams = getattr(self.plan.routine, 'exams', None)
            if exams is None:
                return None
            if hasattr(exams, 'all'):
                for exam in exams.all():
                    if getattr(exam, 'course_code', None) == self.course_code:
                        return getattr(exam, 'exam_date', None)
                    if getattr(exam, 'subject', None) == self.course_code:
                        return getattr(exam, 'exam_date', None)
        except Exception:
            return None
        return None

    @property
    def days_until_exam(self):
        exam_date = self._get_exam_date()
        if not exam_date:
            return None
        return (exam_date - date.today()).days


class DailyTask(models.Model):
    course_plan = models.ForeignKey(CoursePlan, on_delete=models.CASCADE, related_name='daily_tasks')
    date = models.DateField()
    hours = models.FloatField(default=1.0)
    is_completed = models.BooleanField(default=False)

    class Meta:
        ordering = ['date', 'id']

    def __str__(self):
        return f"{self.course_plan.course_code} - {self.date} ({self.hours}h)"
