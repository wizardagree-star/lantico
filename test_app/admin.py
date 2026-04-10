from django.contrib import admin
from .models import Case, Option, TestSession, Answer

class OptionInline(admin.TabularInline):
    model = Option
    extra = 0

@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ("case_id", "dimension", "order")
    list_filter = ("dimension",)
    inlines = [OptionInline]

@admin.register(TestSession)
class TestSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "started_at", "completed_at")

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("session", "case", "dimension", "selected_option", "raw_score")
