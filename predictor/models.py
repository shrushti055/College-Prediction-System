from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class CollegeCutoff(models.Model):
    """One training/recommendation row from dataset.csv."""
    record_id = models.IntegerField(null=True, blank=True)
    year = models.IntegerField(db_index=True)
    exam = models.CharField(max_length=40, db_index=True)  # MHT CET / JEE
    round_name = models.CharField(max_length=40, db_index=True)
    category = models.CharField(max_length=40, db_index=True)
    home_region = models.CharField(max_length=120, blank=True, db_index=True)
    university_quota = models.CharField(max_length=80, blank=True, db_index=True)
    stream = models.CharField(max_length=80, blank=True)
    branch = models.CharField(max_length=180, db_index=True)
    college_code = models.CharField(max_length=40, blank=True, db_index=True)
    college_name = models.CharField(max_length=255, db_index=True)
    college_type = models.CharField(max_length=60, blank=True, db_index=True)  # Govt / Private
    city = models.CharField(max_length=80, blank=True, db_index=True)
    district = models.CharField(max_length=80, blank=True)
    state = models.CharField(max_length=80, blank=True)
    naac_grade = models.CharField(max_length=20, blank=True)
    naac_score = models.FloatField(default=0)
    nirf_rank = models.IntegerField(default=9999)
    fees_per_year = models.IntegerField(default=0)
    total_seats = models.IntegerField(default=0)
    category_seats = models.IntegerField(default=0)
    student_percentile = models.FloatField(default=0)
    student_rank = models.IntegerField(default=0)
    aptitude_score = models.IntegerField(default=0)
    aptitude_stream_suitability = models.CharField(max_length=80, blank=True)
    closing_percentile = models.FloatField(default=0)
    closing_rank = models.IntegerField(default=0)
    previous_year_closing_percentile = models.FloatField(default=0)
    previous_year_closing_rank = models.IntegerField(default=0)
    cutoff_trend_3yr = models.CharField(max_length=255, blank=True)
    admission_probability = models.CharField(max_length=40, blank=True)
    source_row_no = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['college_name', 'branch', '-year']
        indexes = [
            models.Index(fields=['exam', 'category', 'branch']),
            models.Index(fields=['city', 'college_type']),
            models.Index(fields=['naac_score', 'nirf_rank']),
            models.Index(fields=['fees_per_year']),
        ]
        verbose_name = 'College Cutoff Dataset Row'
        verbose_name_plural = 'College Cutoff Dataset Rows'

    def __str__(self):
        return f'{self.college_name} | {self.exam} | {self.branch} | {self.category} | {self.round_name}'


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=120, blank=True)
    exam = models.CharField(max_length=40, blank=True)
    category = models.CharField(max_length=40, blank=True)
    home_region = models.CharField(max_length=120, blank=True)
    university_quota = models.CharField(max_length=80, blank=True)
    preferred_stream = models.CharField(max_length=80, blank=True)
    preferred_branch = models.CharField(max_length=180, blank=True)
    percentile = models.FloatField(default=0)
    rank = models.IntegerField(default=0)
    aptitude_score = models.IntegerField(default=0)
    city_preference = models.CharField(max_length=80, blank=True)
    max_fees = models.IntegerField(default=0)

    # FR6 RIASEC / Career assessment result summary
    riasec_realistic = models.IntegerField(default=0)
    riasec_investigative = models.IntegerField(default=0)
    riasec_artistic = models.IntegerField(default=0)
    riasec_social = models.IntegerField(default=0)
    riasec_enterprising = models.IntegerField(default=0)
    riasec_conventional = models.IntegerField(default=0)
    dominant_riasec_code = models.CharField(max_length=10, blank=True)
    career_cluster = models.CharField(max_length=120, blank=True)
    recommended_streams = models.CharField(max_length=255, blank=True)
    career_report_text = models.TextField(blank=True)

    def __str__(self):
        return self.full_name or self.user.username


class PredictionHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    exam = models.CharField(max_length=40)
    category = models.CharField(max_length=40)
    home_region = models.CharField(max_length=120, blank=True)
    university_quota = models.CharField(max_length=80, blank=True)
    branch = models.CharField(max_length=180)
    percentile = models.FloatField()
    rank = models.IntegerField(default=0)
    aptitude_score = models.IntegerField(default=0)
    round_name = models.CharField(max_length=40)
    city = models.CharField(max_length=80, blank=True)
    college_type = models.CharField(max_length=60, blank=True)
    max_fees = models.IntegerField(default=0)
    min_naac_score = models.FloatField(default=0)
    max_nirf_rank = models.IntegerField(default=0)
    top_result = models.CharField(max_length=255, blank=True)
    result_count = models.IntegerField(default=0)
    result_snapshot_json = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.percentile} - {self.branch} - {self.category}'


class ChatMessage(models.Model):
    """Stores each AI/Chatbot counselling conversation message."""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    question = models.TextField()
    answer = models.TextField()
    intent = models.CharField(max_length=80, blank=True)
    used_student_profile = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Chatbot Message'
        verbose_name_plural = 'Chatbot Messages'

    def __str__(self):
        return f'{self.user or "Guest"} - {self.intent or "query"}'


class CounsellorProfile(models.Model):
    """FR5.1 Human counsellor profile and availability summary."""
    SESSION_CHOICES = [
        ('Video', 'Video'),
        ('Chat', 'Chat'),
        ('Phone Call', 'Phone Call'),
        ('In Person', 'In Person'),
    ]

    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    certification_id = models.CharField(max_length=80, blank=True)
    qualification = models.CharField(max_length=180)
    specialization = models.CharField(max_length=180, default='Engineering Admission Counselling')
    experience_years = models.IntegerField(default=0)
    languages = models.CharField(max_length=120, default='English, Hindi, Marathi')
    city = models.CharField(max_length=80, blank=True)
    supported_modes = models.CharField(max_length=120, default='Video, Chat, Phone Call')
    fee_per_session = models.IntegerField(default=499)
    rating = models.FloatField(default=4.5)
    available_days = models.CharField(max_length=120, default='Mon-Sat')
    available_time = models.CharField(max_length=120, default='10:00 AM - 06:00 PM')
    bio = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-rating', 'fee_per_session', 'name']

    def __str__(self):
        return f'{self.name} ({self.specialization})'


class CounsellingSession(models.Model):
    """FR4.4 + FR5 booking request and counselling session record."""
    MODE_CHOICES = [
        ('Video', 'Video'),
        ('Chat', 'Chat'),
        ('Phone Call', 'Phone Call'),
        ('In Person', 'In Person'),
    ]
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Payment Pending', 'Payment Pending'),
        ('Confirmed', 'Confirmed'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('Unpaid', 'Unpaid'),
        ('Paid', 'Paid'),
        ('Failed', 'Failed'),
        ('Refunded', 'Refunded'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    counsellor = models.ForeignKey(CounsellorProfile, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    student_name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20)
    preferred_date = models.DateField()
    preferred_time = models.TimeField()
    mode = models.CharField(max_length=40, choices=MODE_CHOICES, default='Video')
    topic = models.CharField(max_length=180, default='College Admission Counselling')
    student_summary = models.TextField(blank=True)
    predicted_college_summary = models.TextField(blank=True)
    aptitude_summary = models.TextField(blank=True)
    meeting_link = models.URLField(blank=True)
    amount = models.IntegerField(default=0)
    status = models.CharField(max_length=40, choices=STATUS_CHOICES, default='Payment Pending')
    payment_status = models.CharField(max_length=40, choices=PAYMENT_STATUS_CHOICES, default='Unpaid')
    admin_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Human Counselling Session'
        verbose_name_plural = 'Human Counselling Sessions'

    def __str__(self):
        return f'{self.student_name} - {self.preferred_date} {self.preferred_time}'


class PaymentTransaction(models.Model):
    """FR5.2 Demo payment transaction. Replace with Razorpay/Stripe in production."""
    STATUS_CHOICES = [
        ('Success', 'Success'),
        ('Failed', 'Failed'),
        ('Pending', 'Pending'),
    ]

    session = models.ForeignKey(CounsellingSession, on_delete=models.CASCADE, related_name='payments')
    created_at = models.DateTimeField(auto_now_add=True)
    amount = models.IntegerField()
    payment_method = models.CharField(max_length=40, default='Demo Payment')
    transaction_reference = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Pending')

    def __str__(self):
        return f'{self.session.student_name} - {self.amount} - {self.status}'


class AptitudeQuestion(models.Model):
    """FR6.1 RIASEC aptitude/psychometric assessment question."""
    RIASEC_CHOICES = [
        ('R', 'Realistic'),
        ('I', 'Investigative'),
        ('A', 'Artistic'),
        ('S', 'Social'),
        ('E', 'Enterprising'),
        ('C', 'Conventional'),
    ]
    question_text = models.CharField(max_length=255)
    riasec_type = models.CharField(max_length=1, choices=RIASEC_CHOICES)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['riasec_type', 'id']

    def __str__(self):
        return f'{self.riasec_type}: {self.question_text[:60]}'


class AptitudeResult(models.Model):
    """FR6.2 Career Suitability Report."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    realistic = models.IntegerField(default=0)
    investigative = models.IntegerField(default=0)
    artistic = models.IntegerField(default=0)
    social = models.IntegerField(default=0)
    enterprising = models.IntegerField(default=0)
    conventional = models.IntegerField(default=0)
    dominant_code = models.CharField(max_length=3, blank=True)
    secondary_code = models.CharField(max_length=3, blank=True)
    career_cluster = models.CharField(max_length=120, blank=True)
    recommended_stream = models.CharField(max_length=120, blank=True)
    recommended_branches = models.TextField(blank=True)
    strengths = models.TextField(blank=True)
    report_text = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} - {self.dominant_code} - {self.created_at:%d-%m-%Y}'


class TrendingCourse(models.Model):
    """FR7 Trending industry course analysis using demand index formula."""
    course_name = models.CharField(max_length=160)
    career_path = models.CharField(max_length=160)
    stream = models.CharField(max_length=80, default='Engineering')
    branch_keywords = models.CharField(max_length=255, help_text='Comma separated branch keywords used to find matching colleges')
    average_salary_lpa = models.FloatField(default=0)
    job_growth_rate = models.FloatField(default=0)
    search_interest_growth = models.FloatField(default=0)
    course_enrollment_growth = models.FloatField(default=0)
    salary_growth = models.FloatField(default=0)
    required_skills = models.TextField(blank=True)
    demand_index = models.FloatField(default=0)
    leading_colleges = models.TextField(blank=True)
    source_note = models.CharField(max_length=255, default='Sample project dataset')
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-demand_index', '-average_salary_lpa']

    def calculate_demand_index(self):
        return round(
            (0.4 * float(self.job_growth_rate or 0)) +
            (0.3 * float(self.search_interest_growth or 0)) +
            (0.2 * float(self.course_enrollment_growth or 0)) +
            (0.1 * float(self.salary_growth or 0)),
            2,
        )

    def save(self, *args, **kwargs):
        self.demand_index = self.calculate_demand_index()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.course_name} - {self.demand_index}'
