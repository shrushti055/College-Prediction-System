import json
import uuid
from datetime import date

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import (
    PredictionForm,
    RegisterForm,
    ChatbotForm,
    CounsellingBookingForm,
    PaymentForm,
    CounsellorFilterForm,
    AptitudeAnswerForm,
)
from .models import (
    CollegeCutoff,
    PredictionHistory,
    StudentProfile,
    ChatMessage,
    CounsellingSession,
    CounsellorProfile,
    PaymentTransaction,
    AptitudeQuestion,
    AptitudeResult,
    TrendingCourse,
)
from .ml_utils import load_metadata, prepare_dataset, recommend_colleges, train_cutoff_model
from .chatbot_utils import answer_chatbot_question, get_student_summary


RIASEC_INFO = {
    'R': {
        'name': 'Realistic',
        'cluster': 'Practical Engineering & Technical Operations',
        'stream': 'Engineering / Technology',
        'branches': ['Mechanical Engineering', 'Civil Engineering', 'Electrical Engineering', 'Robotics Engineering'],
        'strengths': 'Hands-on problem solving, machines, tools, physical systems and field work.',
    },
    'I': {
        'name': 'Investigative',
        'cluster': 'Research, AI, Data & Analytical Technology',
        'stream': 'Engineering / Computer Science / Data Science',
        'branches': ['Computer Engineering', 'Artificial Intelligence and Data Science', 'Information Technology', 'Cyber Security'],
        'strengths': 'Analysis, research, logic, mathematics, experiments and complex problem solving.',
    },
    'A': {
        'name': 'Artistic',
        'cluster': 'Design, Digital Product & Creative Technology',
        'stream': 'Design / Architecture / Computer Applications',
        'branches': ['Computer Engineering', 'Information Technology', 'Architecture', 'Design'],
        'strengths': 'Creativity, visual thinking, communication, design and innovation.',
    },
    'S': {
        'name': 'Social',
        'cluster': 'Healthcare, Education & People-Centric Services',
        'stream': 'Medical / Education / Management',
        'branches': ['Biomedical Engineering', 'Computer Engineering', 'Management Studies'],
        'strengths': 'Helping, teaching, counselling, teamwork and communication.',
    },
    'E': {
        'name': 'Enterprising',
        'cluster': 'Business, Product Management & Entrepreneurship',
        'stream': 'Management / Engineering Management',
        'branches': ['Computer Engineering', 'Information Technology', 'Electronics and Telecommunication'],
        'strengths': 'Leadership, persuasion, business planning, product thinking and decision making.',
    },
    'C': {
        'name': 'Conventional',
        'cluster': 'Data Operations, Finance Technology & Process Management',
        'stream': 'Commerce / IT / Data Analytics',
        'branches': ['Information Technology', 'Computer Engineering', 'Data Science'],
        'strengths': 'Organization, data handling, planning, accuracy, reporting and structured work.',
    },
}


DEFAULT_APTITUDE_QUESTIONS = [
    ('R', 'I enjoy building, repairing, assembling or testing machines/devices.'),
    ('R', 'I prefer practical laboratory or field work over only theory.'),
    ('R', 'I like solving problems involving tools, circuits, machines or construction.'),
    ('I', 'I enjoy mathematics, coding, analytics, research or scientific reasoning.'),
    ('I', 'I like investigating why something works and finding evidence-based answers.'),
    ('I', 'I am interested in AI, data science, cybersecurity or advanced computing.'),
    ('A', 'I enjoy designing interfaces, presentations, content, graphics or creative products.'),
    ('A', 'I prefer tasks where I can generate new ideas and visualize solutions.'),
    ('A', 'I like combining technology with creativity or user experience.'),
    ('S', 'I enjoy helping classmates understand concepts or solve problems.'),
    ('S', 'I prefer careers that involve communication, guidance or public impact.'),
    ('S', 'I am comfortable working in teams and mentoring others.'),
    ('E', 'I like leadership, entrepreneurship, marketing or product decision-making.'),
    ('E', 'I enjoy convincing people, presenting ideas and taking initiative.'),
    ('E', 'I can imagine managing a project, team, startup or product.'),
    ('C', 'I like organizing data, reports, schedules, records or financial information.'),
    ('C', 'I prefer clear rules, structured work and accuracy-oriented tasks.'),
    ('C', 'I am comfortable with databases, dashboards, documentation or process tracking.'),
]


DEFAULT_TRENDING_COURSES = [
    {
        'course_name': 'Artificial Intelligence and Data Science',
        'career_path': 'AI Engineer / Data Scientist',
        'branch_keywords': 'Artificial Intelligence,Data Science,Computer Engineering,Information Technology',
        'average_salary_lpa': 9.5,
        'job_growth_rate': 36,
        'search_interest_growth': 42,
        'course_enrollment_growth': 31,
        'salary_growth': 20,
        'required_skills': 'Python, Machine Learning, Deep Learning, SQL, Statistics, Cloud, MLOps',
    },
    {
        'course_name': 'Cyber Security',
        'career_path': 'Security Analyst / SOC Engineer',
        'branch_keywords': 'Cyber Security,Computer Engineering,Information Technology',
        'average_salary_lpa': 8.2,
        'job_growth_rate': 34,
        'search_interest_growth': 38,
        'course_enrollment_growth': 26,
        'salary_growth': 18,
        'required_skills': 'Network Security, Linux, SIEM, Python, Cloud Security, Ethical Hacking',
    },
    {
        'course_name': 'Cloud Computing and DevOps',
        'career_path': 'Cloud Engineer / DevOps Engineer',
        'branch_keywords': 'Computer Engineering,Information Technology,Electronics and Telecommunication',
        'average_salary_lpa': 8.7,
        'job_growth_rate': 32,
        'search_interest_growth': 35,
        'course_enrollment_growth': 24,
        'salary_growth': 17,
        'required_skills': 'AWS/Azure/GCP, Docker, Kubernetes, CI/CD, Linux, Terraform',
    },
    {
        'course_name': 'Electronics and VLSI',
        'career_path': 'Embedded/VLSI Engineer',
        'branch_keywords': 'Electronics and Telecommunication,Electrical Engineering',
        'average_salary_lpa': 7.2,
        'job_growth_rate': 25,
        'search_interest_growth': 22,
        'course_enrollment_growth': 18,
        'salary_growth': 14,
        'required_skills': 'Embedded C, Verilog, Digital Electronics, Microcontrollers, PCB Design',
    },
    {
        'course_name': 'Robotics and Automation',
        'career_path': 'Robotics Engineer / Automation Engineer',
        'branch_keywords': 'Mechanical Engineering,Electronics and Telecommunication,Computer Engineering',
        'average_salary_lpa': 7.8,
        'job_growth_rate': 28,
        'search_interest_growth': 30,
        'course_enrollment_growth': 19,
        'salary_growth': 15,
        'required_skills': 'Python, ROS, Control Systems, CAD, Sensors, Computer Vision, IoT',
    },
]


def dataset_summary():
    try:
        if CollegeCutoff.objects.exists():
            return {
                'rows': CollegeCutoff.objects.count(),
                'colleges': CollegeCutoff.objects.values('college_name').distinct().count(),
                'branches': CollegeCutoff.objects.values('branch').distinct().count(),
                'categories': CollegeCutoff.objects.values('category').distinct().count(),
                'exams': CollegeCutoff.objects.values('exam').distinct().count(),
                'cities': CollegeCutoff.objects.values('city').distinct().count(),
                'years': ', '.join(map(str, CollegeCutoff.objects.values_list('year', flat=True).distinct().order_by('year'))),
                'source': 'SQLite database',
            }
        df = prepare_dataset()
        return {
            'rows': len(df),
            'colleges': df['college_name'].nunique(),
            'branches': df['branch'].nunique(),
            'categories': df['category'].nunique(),
            'exams': df['exam'].nunique(),
            'cities': df['city'].nunique(),
            'years': ', '.join(map(str, sorted(df['year'].unique()))),
            'source': 'data/dataset.csv',
        }
    except Exception as exc:
        return {
            'rows': 0,
            'colleges': 0,
            'branches': 0,
            'categories': 0,
            'exams': 0,
            'cities': 0,
            'years': '-',
            'source': f'Dataset error: {exc}',
        }


def create_default_aptitude_questions():
    if AptitudeQuestion.objects.exists():
        return
    AptitudeQuestion.objects.bulk_create([
        AptitudeQuestion(riasec_type=code, question_text=text) for code, text in DEFAULT_APTITUDE_QUESTIONS
    ])


def create_default_counsellors():
    if CounsellorProfile.objects.exists():
        return
    CounsellorProfile.objects.bulk_create([
        CounsellorProfile(
            name='Dr. Anjali Deshmukh', city='Pune', qualification='Ph.D. Education Psychology, Certified Career Counsellor',
            specialization='Engineering CAP & Career Assessment', experience_years=12, fee_per_session=799, rating=4.8,
            bio='Specialist in Maharashtra CAP counselling, engineering branch selection and aptitude-based career planning.'
        ),
        CounsellorProfile(
            name='Prof. Rohan Kulkarni', city='Mumbai', qualification='M.Tech, Certified Admission Counsellor',
            specialization='JEE / MHT CET College Option Form', experience_years=9, fee_per_session=699, rating=4.7,
            bio='Helps students compare colleges using cutoff, fees, NIRF/NAAC, placement and location preferences.'
        ),
        CounsellorProfile(
            name='Ms. Sneha Patil', city='Pune', qualification='M.A. Psychology, RIASEC Career Guidance Certified',
            specialization='Aptitude & Psychometric Counselling', experience_years=7, fee_per_session=599, rating=4.6,
            bio='Focuses on aptitude reports, RIASEC assessment and course-career mapping.'
        ),
    ])


def create_default_trending_courses():
    if TrendingCourse.objects.exists():
        return
    for data in DEFAULT_TRENDING_COURSES:
        TrendingCourse.objects.create(**data)


def refresh_leading_colleges_for_trends():
    """Find leading colleges for each trending course from current college dataset."""
    for course in TrendingCourse.objects.all():
        keywords = [k.strip().lower() for k in course.branch_keywords.split(',') if k.strip()]
        qs = CollegeCutoff.objects.all()
        if keywords:
            query = Q()
            for kw in keywords:
                query |= Q(branch__icontains=kw)
            qs = qs.filter(query)
        latest_year = qs.order_by('-year').values_list('year', flat=True).first()
        if latest_year:
            qs = qs.filter(year=latest_year)
        rows = qs.order_by('nirf_rank', '-naac_score', 'fees_per_year').values('college_name', 'city', 'branch', 'nirf_rank', 'naac_grade')[:5]
        course.leading_colleges = '\n'.join(
            f"{r['college_name']} ({r['city']}) - {r['branch']} | NIRF {r['nirf_rank']} | NAAC {r['naac_grade']}"
            for r in rows
        )
        course.save()


def home(request):
    return render(request, 'predictor/home.html', {
        'summary': dataset_summary(),
        'metadata': load_metadata(),
    })


@require_http_methods(['GET', 'POST'])
def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data.get('email', '')
            user.first_name = form.cleaned_data.get('full_name', '')
            user.save()
            StudentProfile.objects.create(user=user, full_name=form.cleaned_data.get('full_name', ''))
            login(request, user)
            messages.success(request, 'Registration successful. Now enter your exam details for recommendation.')
            return redirect('predict')
    else:
        form = RegisterForm()
    return render(request, 'predictor/register.html', {'form': form})


@login_required
def predict(request):
    results = []
    submitted = None

    if request.method == 'POST':
        form = PredictionForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            results = recommend_colleges(
                percentile=cd['percentile'],
                rank=cd.get('rank') or 0,
                exam=cd['exam'],
                category=cd['category'],
                home_region=cd.get('home_region') or '',
                university_quota=cd.get('university_quota') or '',
                branch=cd['branch'],
                round_name=cd['round_name'],
                city=cd.get('city') or '',
                college_type=cd.get('college_type') or '',
                max_fees=cd.get('max_fees') or 0,
                min_naac_score=cd.get('min_naac_score') or 0,
                max_nirf_rank=cd.get('max_nirf_rank') or 0,
                aptitude_score=cd.get('aptitude_score') or 0,
                top_n=cd.get('top_n') or 30,
            )
            submitted = cd

            profile, _ = StudentProfile.objects.get_or_create(user=request.user)
            profile.full_name = profile.full_name or request.user.first_name or request.user.username
            profile.exam = cd['exam']
            profile.category = cd['category']
            profile.home_region = cd.get('home_region') or ''
            profile.university_quota = cd.get('university_quota') or ''
            profile.preferred_stream = 'Engineering'
            profile.preferred_branch = cd['branch']
            profile.percentile = cd['percentile']
            profile.rank = cd.get('rank') or 0
            profile.aptitude_score = cd.get('aptitude_score') or 0
            profile.city_preference = cd.get('city') or ''
            profile.max_fees = cd.get('max_fees') or 0
            profile.save()

            PredictionHistory.objects.create(
                user=request.user,
                exam=cd['exam'],
                category=cd['category'],
                home_region=cd.get('home_region') or '',
                university_quota=cd.get('university_quota') or '',
                branch=cd['branch'],
                percentile=cd['percentile'],
                rank=cd.get('rank') or 0,
                aptitude_score=cd.get('aptitude_score') or 0,
                round_name=cd['round_name'],
                city=cd.get('city') or '',
                college_type=cd.get('college_type') or '',
                max_fees=cd.get('max_fees') or 0,
                min_naac_score=cd.get('min_naac_score') or 0,
                max_nirf_rank=cd.get('max_nirf_rank') or 0,
                top_result=results[0]['college_name'] if results else '',
                result_count=len(results),
                result_snapshot_json=json.dumps(results[:10]),
            )

            if not results:
                messages.warning(request, 'No exact records found. Try removing filters like city, fees, NAAC or NIRF.')
        else:
            messages.error(request, 'Please correct the highlighted input fields.')
    else:
        initial = {}
        try:
            profile = StudentProfile.objects.get(user=request.user)
            initial = {
                'exam': profile.exam or None,
                'percentile': profile.percentile or None,
                'rank': profile.rank or None,
                'category': profile.category or None,
                'home_region': profile.home_region or None,
                'university_quota': profile.university_quota or None,
                'branch': profile.preferred_branch or None,
                'city': profile.city_preference or None,
                'max_fees': profile.max_fees or None,
                'aptitude_score': profile.aptitude_score or None,
            }
        except StudentProfile.DoesNotExist:
            pass
        form = PredictionForm(initial=initial)

    return render(request, 'predictor/predict.html', {
        'form': form,
        'results': results,
        'submitted': submitted,
        'metadata': load_metadata(),
        'summary': dataset_summary(),
    })


@login_required
def history(request):
    rows = PredictionHistory.objects.filter(user=request.user)[:30]
    return render(request, 'predictor/history.html', {'rows': rows})


@require_http_methods(['GET', 'POST'])
def train_model_view(request):
    metadata = load_metadata()
    if request.method == 'POST':
        try:
            metadata = train_cutoff_model()
            messages.success(request, 'ML model trained successfully. Prediction page is ready.')
        except Exception as exc:
            messages.error(request, f'Model training failed: {exc}')
    return render(request, 'predictor/train.html', {
        'metadata': metadata,
        'summary': dataset_summary(),
    })


@require_http_methods(['POST'])
def load_dataset_view(request):
    try:
        df = prepare_dataset()
        CollegeCutoff.objects.all().delete()
        objects = []
        for row in df.itertuples(index=False):
            data = row._asdict()
            objects.append(CollegeCutoff(
                record_id=data.get('record_id'),
                year=int(data['year']),
                exam=data['exam'],
                round_name=data['round'],
                category=data['category'],
                home_region=data['home_region'],
                university_quota=data['university_quota'],
                stream=data['stream'],
                branch=data['branch'],
                college_code=str(data['college_code']),
                college_name=data['college_name'],
                college_type=data['college_type'],
                city=data['city'],
                district=data['district'],
                state=data['state'],
                naac_grade=data['naac_grade'],
                naac_score=float(data['naac_score']),
                nirf_rank=int(data['nirf_rank']),
                fees_per_year=int(data['fees_per_year']),
                total_seats=int(data['total_seats']),
                category_seats=int(data['category_seats']),
                student_percentile=float(data['student_percentile']),
                student_rank=int(data['student_rank']),
                aptitude_score=int(data['aptitude_score']),
                aptitude_stream_suitability=data['aptitude_stream_suitability'],
                closing_percentile=float(data['closing_percentile']),
                closing_rank=int(data['closing_rank']),
                previous_year_closing_percentile=float(data['previous_year_closing_percentile']),
                previous_year_closing_rank=int(data['previous_year_closing_rank']),
                cutoff_trend_3yr=data['cutoff_trend_3yr'],
                admission_probability=data['admission_probability'],
                source_row_no=len(objects) + 2,
            ))
        CollegeCutoff.objects.bulk_create(objects, batch_size=500)
        messages.success(request, f'Dataset loaded into SQLite successfully. Rows inserted: {len(objects)}')
    except Exception as exc:
        messages.error(request, f'Dataset load failed: {exc}')
    return redirect('train_model_view')


@login_required
def chatbot(request):
    """AI/Chatbot Counselling page covering FR4.1-FR4.4."""
    response = None
    form = ChatbotForm()
    if request.method == 'POST':
        form = ChatbotForm(request.POST)
        if form.is_valid():
            question = form.cleaned_data['question']
            response = answer_chatbot_question(question, request.user)
            ChatMessage.objects.create(
                user=request.user,
                question=question,
                answer=response['answer'],
                intent=response.get('intent', ''),
                used_student_profile=response.get('used_profile', False),
            )
            form = ChatbotForm()

    chats = ChatMessage.objects.filter(user=request.user)[:20]
    profile_data, profile_summary = get_student_summary(request.user)
    return render(request, 'predictor/chatbot.html', {
        'form': form,
        'response': response,
        'chats': chats,
        'profile_summary': profile_summary,
        'has_profile': bool(profile_data),
    })


def counsellors(request):
    """FR5.1: show certified counsellor profiles and availability."""
    create_default_counsellors()
    form = CounsellorFilterForm(request.GET or None)
    rows = CounsellorProfile.objects.filter(is_active=True)
    if form.is_valid():
        city = form.cleaned_data.get('city')
        specialization = form.cleaned_data.get('specialization')
        if city:
            rows = rows.filter(city__icontains=city)
        if specialization:
            rows = rows.filter(specialization__icontains=specialization)
    return render(request, 'predictor/counsellors.html', {'form': form, 'rows': rows})


@login_required
def book_counselling(request, counsellor_id=None):
    """FR5.2 booking handoff. Payment is completed on next page."""
    create_default_counsellors()
    profile_data, profile_summary = get_student_summary(request.user)
    counsellor = CounsellorProfile.objects.filter(id=counsellor_id, is_active=True).first() if counsellor_id else None
    latest_prediction = PredictionHistory.objects.filter(user=request.user).first()
    latest_aptitude = AptitudeResult.objects.filter(user=request.user).first()
    initial = {
        'student_name': request.user.first_name or request.user.username,
        'email': request.user.email,
        'topic': 'College Prediction & CAP Counselling',
    }
    if counsellor:
        initial['counsellor'] = counsellor.id
    if request.method == 'POST':
        form = CounsellingBookingForm(request.POST, counsellor_id=counsellor_id)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.user = request.user
            if not booking.counsellor:
                booking.counsellor = CounsellorProfile.objects.filter(is_active=True).order_by('-rating').first()
            booking.amount = booking.counsellor.fee_per_session if booking.counsellor else 499
            booking.student_summary = profile_summary
            booking.predicted_college_summary = latest_prediction.result_snapshot_json if latest_prediction else 'No prediction history found.'
            if latest_aptitude:
                booking.aptitude_summary = f'{latest_aptitude.dominant_code} | {latest_aptitude.career_cluster} | {latest_aptitude.recommended_branches}'
            else:
                booking.aptitude_summary = 'Aptitude test not completed yet.'
            booking.status = 'Payment Pending'
            booking.payment_status = 'Unpaid'
            booking.save()
            messages.success(request, 'Booking created. Please complete the demo payment to confirm your counselling session.')
            return redirect('payment_checkout', session_id=booking.id)
    else:
        form = CounsellingBookingForm(initial=initial, counsellor_id=counsellor_id)
    return render(request, 'predictor/book_counselling.html', {
        'form': form,
        'profile_summary': profile_summary,
        'selected_counsellor': counsellor,
        'latest_prediction': latest_prediction,
        'latest_aptitude': latest_aptitude,
    })


@login_required
def payment_checkout(request, session_id):
    """FR5.2: demo secure payment flow. Replace this with Razorpay/Stripe keys in production."""
    session = get_object_or_404(CounsellingSession, id=session_id, user=request.user)
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            ref = 'PAY-' + uuid.uuid4().hex[:10].upper()
            PaymentTransaction.objects.create(
                session=session,
                amount=session.amount,
                payment_method=form.cleaned_data['payment_method'],
                transaction_reference=ref,
                status='Success',
            )
            session.payment_status = 'Paid'
            session.status = 'Confirmed'
            session.meeting_link = f'https://meet.example.com/session-{session.id}-{uuid.uuid4().hex[:6]}'
            session.save()
            messages.success(request, f'Demo payment successful. Session confirmed. Transaction: {ref}')
            return redirect('my_counselling_sessions')
    else:
        form = PaymentForm(initial={'payer_name': request.user.first_name or request.user.username})
    return render(request, 'predictor/payment_checkout.html', {'form': form, 'session': session})


@login_required
def my_counselling_sessions(request):
    rows = CounsellingSession.objects.filter(user=request.user)
    return render(request, 'predictor/my_counselling_sessions.html', {'rows': rows})


@login_required
def counsellor_dashboard(request):
    """FR5.3: dashboard for counsellor to view student profiles, predictions and aptitude results."""
    if request.user.is_staff or request.user.is_superuser:
        sessions = CounsellingSession.objects.select_related('user', 'counsellor').all()
        counsellor = None
    else:
        counsellor = CounsellorProfile.objects.filter(user=request.user).first()
        if not counsellor:
            messages.error(request, 'Your login is not mapped to a counsellor profile. Ask admin to link your user account.')
            return redirect('home')
        sessions = CounsellingSession.objects.select_related('user', 'counsellor').filter(counsellor=counsellor)
    return render(request, 'predictor/counsellor_dashboard.html', {
        'sessions': sessions,
        'counsellor': counsellor,
    })


@login_required
def aptitude_test(request):
    """FR6.1: RIASEC-based aptitude test."""
    create_default_aptitude_questions()
    questions = list(AptitudeQuestion.objects.filter(is_active=True))
    if request.method == 'POST':
        form = AptitudeAnswerForm(request.POST, questions=questions)
        if form.is_valid():
            scores = {'R': 0, 'I': 0, 'A': 0, 'S': 0, 'E': 0, 'C': 0}
            for q in questions:
                scores[q.riasec_type] += int(form.cleaned_data.get(f'q_{q.id}', 0))
            ordered = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            dominant_code = ordered[0][0]
            secondary_code = ordered[1][0]
            info = RIASEC_INFO[dominant_code]
            recommended_branches = ', '.join(info['branches'])
            report_text = (
                f"Your dominant RIASEC type is {dominant_code} - {info['name']}. "
                f"This indicates strength in {info['strengths']} Recommended stream: {info['stream']}. "
                f"Recommended branches/courses: {recommended_branches}."
            )
            result = AptitudeResult.objects.create(
                user=request.user,
                realistic=scores['R'], investigative=scores['I'], artistic=scores['A'],
                social=scores['S'], enterprising=scores['E'], conventional=scores['C'],
                dominant_code=dominant_code,
                secondary_code=secondary_code,
                career_cluster=info['cluster'],
                recommended_stream=info['stream'],
                recommended_branches=recommended_branches,
                strengths=info['strengths'],
                report_text=report_text,
            )
            profile, _ = StudentProfile.objects.get_or_create(user=request.user)
            profile.riasec_realistic = scores['R']
            profile.riasec_investigative = scores['I']
            profile.riasec_artistic = scores['A']
            profile.riasec_social = scores['S']
            profile.riasec_enterprising = scores['E']
            profile.riasec_conventional = scores['C']
            profile.dominant_riasec_code = dominant_code
            profile.career_cluster = info['cluster']
            profile.recommended_streams = info['stream']
            profile.career_report_text = report_text
            profile.aptitude_score = int(sum(scores.values()) / max(1, len(questions)) * 20)
            profile.save()
            messages.success(request, 'Aptitude test completed. Career suitability report generated.')
            return redirect('aptitude_result', result_id=result.id)
    else:
        form = AptitudeAnswerForm(questions=questions)
    return render(request, 'predictor/aptitude_test.html', {'form': form, 'questions': questions})


@login_required
def aptitude_result(request, result_id=None):
    result = None
    if result_id:
        result = get_object_or_404(AptitudeResult, id=result_id, user=request.user)
    else:
        result = AptitudeResult.objects.filter(user=request.user).first()
    if not result:
        messages.info(request, 'Please complete the aptitude test first.')
        return redirect('aptitude_test')

    # FR6.3: cross-reference aptitude report with current college prediction dataset.
    branch_terms = [b.strip() for b in result.recommended_branches.split(',') if b.strip()]
    q = Q()
    for term in branch_terms:
        q |= Q(branch__icontains=term)
    college_rows = CollegeCutoff.objects.filter(q) if branch_terms else CollegeCutoff.objects.all()
    latest_year = college_rows.order_by('-year').values_list('year', flat=True).first()
    if latest_year:
        college_rows = college_rows.filter(year=latest_year)
    college_rows = college_rows.order_by('nirf_rank', '-naac_score', 'fees_per_year')[:15]

    return render(request, 'predictor/aptitude_result.html', {
        'result': result,
        'college_rows': college_rows,
    })


def trending_courses(request):
    """FR7: Trending industry course analysis and demand index display."""
    create_default_trending_courses()
    refresh_leading_colleges_for_trends()
    courses = TrendingCourse.objects.all()
    return render(request, 'predictor/trending_courses.html', {
        'courses': courses,
        'formula': 'Demand Index = 0.4 × Job Market Growth + 0.3 × Search Interest Growth + 0.2 × Course Enrollment Growth + 0.1 × Salary Growth',
    })
