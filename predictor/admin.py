from django.contrib import admin
from .models import (
    CollegeCutoff,
    StudentProfile,
    PredictionHistory,
    ChatMessage,
    CounsellorProfile,
    CounsellingSession,
    PaymentTransaction,
    AptitudeQuestion,
    AptitudeResult,
    TrendingCourse,
)


@admin.register(CollegeCutoff)
class CollegeCutoffAdmin(admin.ModelAdmin):
    list_display = (
        'college_name', 'city', 'college_type', 'exam', 'branch', 'category',
        'round_name', 'year', 'closing_percentile', 'previous_year_closing_percentile',
        'naac_grade', 'nirf_rank', 'fees_per_year', 'category_seats'
    )
    list_filter = ('exam', 'year', 'city', 'college_type', 'category', 'home_region', 'university_quota', 'branch', 'round_name')
    search_fields = ('college_name', 'college_code', 'branch', 'city')
    list_per_page = 50


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = (
        'full_name', 'user', 'exam', 'category', 'preferred_branch', 'percentile', 'rank',
        'aptitude_score', 'city_preference', 'dominant_riasec_code', 'career_cluster'
    )
    search_fields = ('full_name', 'user__username')


@admin.register(PredictionHistory)
class PredictionHistoryAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'exam', 'category', 'branch', 'percentile', 'round_name', 'city', 'college_type', 'top_result', 'result_count')
    list_filter = ('exam', 'category', 'branch', 'round_name', 'city', 'college_type')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'intent', 'used_student_profile')
    list_filter = ('intent', 'used_student_profile', 'created_at')
    search_fields = ('question', 'answer', 'user__username')
    readonly_fields = ('created_at',)


@admin.register(CounsellorProfile)
class CounsellorProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'specialization', 'experience_years', 'fee_per_session', 'rating', 'is_active')
    list_filter = ('city', 'specialization', 'is_active')
    search_fields = ('name', 'qualification', 'specialization', 'languages')


@admin.register(CounsellingSession)
class CounsellingSessionAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'student_name', 'counsellor', 'phone', 'preferred_date', 'preferred_time', 'mode', 'amount', 'payment_status', 'status')
    list_filter = ('status', 'payment_status', 'mode', 'preferred_date', 'counsellor')
    search_fields = ('student_name', 'phone', 'email', 'topic', 'student_summary')
    readonly_fields = ('created_at',)


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'session', 'amount', 'payment_method', 'transaction_reference', 'status')
    list_filter = ('status', 'payment_method')
    search_fields = ('transaction_reference', 'session__student_name')


@admin.register(AptitudeQuestion)
class AptitudeQuestionAdmin(admin.ModelAdmin):
    list_display = ('riasec_type', 'question_text', 'is_active')
    list_filter = ('riasec_type', 'is_active')
    search_fields = ('question_text',)


@admin.register(AptitudeResult)
class AptitudeResultAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'dominant_code', 'career_cluster', 'recommended_stream')
    list_filter = ('dominant_code', 'career_cluster')
    search_fields = ('user__username', 'career_cluster', 'recommended_branches')


@admin.register(TrendingCourse)
class TrendingCourseAdmin(admin.ModelAdmin):
    list_display = ('course_name', 'career_path', 'average_salary_lpa', 'job_growth_rate', 'demand_index', 'updated_at')
    list_filter = ('stream', 'career_path')
    search_fields = ('course_name', 'career_path', 'required_skills', 'leading_colleges')
