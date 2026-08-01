from django.core.management.base import BaseCommand
from predictor.models import AptitudeQuestion, CounsellorProfile, TrendingCourse


APTITUDE_QUESTIONS = [
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

COUNSELLORS = [
    {
        'name': 'Dr. Anjali Deshmukh', 'city': 'Pune', 'qualification': 'Ph.D. Education Psychology, Certified Career Counsellor',
        'specialization': 'Engineering CAP & Career Assessment', 'experience_years': 12, 'fee_per_session': 799, 'rating': 4.8,
        'bio': 'Specialist in Maharashtra CAP counselling, engineering branch selection and aptitude-based career planning.'
    },
    {
        'name': 'Prof. Rohan Kulkarni', 'city': 'Mumbai', 'qualification': 'M.Tech, Certified Admission Counsellor',
        'specialization': 'JEE / MHT CET College Option Form', 'experience_years': 9, 'fee_per_session': 699, 'rating': 4.7,
        'bio': 'Helps students compare colleges using cutoff, fees, NIRF/NAAC, placement and location preferences.'
    },
    {
        'name': 'Ms. Sneha Patil', 'city': 'Pune', 'qualification': 'M.A. Psychology, RIASEC Career Guidance Certified',
        'specialization': 'Aptitude & Psychometric Counselling', 'experience_years': 7, 'fee_per_session': 599, 'rating': 4.6,
        'bio': 'Focuses on aptitude reports, RIASEC assessment and course-career mapping.'
    },
]

TRENDING_COURSES = [
    {'course_name': 'Artificial Intelligence and Data Science', 'career_path': 'AI Engineer / Data Scientist', 'branch_keywords': 'Artificial Intelligence,Data Science,Computer Engineering,Information Technology', 'average_salary_lpa': 9.5, 'job_growth_rate': 36, 'search_interest_growth': 42, 'course_enrollment_growth': 31, 'salary_growth': 20, 'required_skills': 'Python, Machine Learning, Deep Learning, SQL, Statistics, Cloud, MLOps'},
    {'course_name': 'Cyber Security', 'career_path': 'Security Analyst / SOC Engineer', 'branch_keywords': 'Cyber Security,Computer Engineering,Information Technology', 'average_salary_lpa': 8.2, 'job_growth_rate': 34, 'search_interest_growth': 38, 'course_enrollment_growth': 26, 'salary_growth': 18, 'required_skills': 'Network Security, Linux, SIEM, Python, Cloud Security, Ethical Hacking'},
    {'course_name': 'Cloud Computing and DevOps', 'career_path': 'Cloud Engineer / DevOps Engineer', 'branch_keywords': 'Computer Engineering,Information Technology,Electronics and Telecommunication', 'average_salary_lpa': 8.7, 'job_growth_rate': 32, 'search_interest_growth': 35, 'course_enrollment_growth': 24, 'salary_growth': 17, 'required_skills': 'AWS/Azure/GCP, Docker, Kubernetes, CI/CD, Linux, Terraform'},
    {'course_name': 'Electronics and VLSI', 'career_path': 'Embedded/VLSI Engineer', 'branch_keywords': 'Electronics and Telecommunication,Electrical Engineering', 'average_salary_lpa': 7.2, 'job_growth_rate': 25, 'search_interest_growth': 22, 'course_enrollment_growth': 18, 'salary_growth': 14, 'required_skills': 'Embedded C, Verilog, Digital Electronics, Microcontrollers, PCB Design'},
    {'course_name': 'Robotics and Automation', 'career_path': 'Robotics Engineer / Automation Engineer', 'branch_keywords': 'Mechanical Engineering,Electronics and Telecommunication,Computer Engineering', 'average_salary_lpa': 7.8, 'job_growth_rate': 28, 'search_interest_growth': 30, 'course_enrollment_growth': 19, 'salary_growth': 15, 'required_skills': 'Python, ROS, Control Systems, CAD, Sensors, Computer Vision, IoT'},
]


class Command(BaseCommand):
    help = 'Seed FR5 counsellors, FR6 aptitude questions and FR7 trending course records.'

    def handle(self, *args, **options):
        q_count = 0
        for code, text in APTITUDE_QUESTIONS:
            _, created = AptitudeQuestion.objects.get_or_create(riasec_type=code, question_text=text)
            q_count += int(created)

        c_count = 0
        for row in COUNSELLORS:
            _, created = CounsellorProfile.objects.get_or_create(name=row['name'], defaults=row)
            c_count += int(created)

        t_count = 0
        for row in TRENDING_COURSES:
            _, created = TrendingCourse.objects.get_or_create(course_name=row['course_name'], defaults=row)
            t_count += int(created)

        self.stdout.write(self.style.SUCCESS('Career/counselling seed data loaded successfully.'))
        self.stdout.write(f'Aptitude questions created : {q_count}')
        self.stdout.write(f'Counsellors created        : {c_count}')
        self.stdout.write(f'Trending courses created   : {t_count}')
