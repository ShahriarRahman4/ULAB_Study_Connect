from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class ActiveSession(Session):
    class Meta:
        proxy = True
        verbose_name = "Active Session"
        verbose_name_plural = "Active Sessions"


class Department(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Course(models.Model):
    DIFFICULTY_CHOICES = [
        (1, "Very Easy"),
        (2, "Easy"),
        (3, "Moderate"),
        (4, "Hard"),
        (5, "Very Hard"),
    ]

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name="courses"
    )
    semester = models.IntegerField()
    difficulty = models.IntegerField(choices=DIFFICULTY_CHOICES, default=3)

    class Meta:
        ordering = ["department", "semester", "code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class UserProfile(models.Model):
    SEMESTER_CHOICES = [(i, f"Semester {i}") for i in range(1, 13)]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
    )
    semester = models.IntegerField(choices=SEMESTER_CHOICES, null=True, blank=True)
    display_name = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return self.get_display_name()

    def get_display_name(self):
        if self.display_name:
            return self.display_name
        if self.user.get_full_name():
            return self.user.get_full_name()
        return self.user.username

    def save(self, *args, **kwargs):
        if not self.display_name:
            if self.user.get_full_name():
                self.display_name = self.user.get_full_name()
            else:
                self.display_name = self.user.username
        super().save(*args, **kwargs)
