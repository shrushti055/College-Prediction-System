from __future__ import annotations

import re
from typing import Dict, List, Tuple

from .models import CollegeCutoff, StudentProfile
from .ml_utils import prepare_dataset, recommend_colleges


FAQS = {
    'documents': (
        'Common documents for admission counselling: SSC marksheet, HSC marksheet, CET/JEE score card, '
        'category certificate if applicable, caste validity, non-creamy layer for OBC/VJNT/SBC where applicable, domicile, '
        'income certificate for EWS/TFWS/scholarship, Aadhaar, passport photo, and allotment letter.'
    ),
    'cap': (
        'CAP process usually includes registration, document verification, option form filling, seat allotment, acceptance/freezing, '
        'reporting to institute, and fee payment. Always verify final dates on official counselling portal.'
    ),
    'home university': (
        'Home University quota is generally based on the candidate\'s qualifying region/university. It can improve chances in colleges '
        'belonging to the same university region when seats are reserved under that quota.'
    ),
    'naac': 'NAAC grade/score indicates institutional quality assessment. Higher NAAC score is generally better.',
    'nirf': 'NIRF rank is a national ranking indicator. Lower rank number means better ranked institution.',
    'fees': 'Fees in this project are shown per year from the dataset. Final fees must be verified from college admission office.',
    'cutoff': 'Cutoff means last admitted percentile/rank for a specific college, branch, category, quota, exam and round.',
}


def _dataset_records() -> List[Dict]:
    if CollegeCutoff.objects.exists():
        return list(CollegeCutoff.objects.all().values())
    df = prepare_dataset()
    records = df.to_dict('records')
    for row in records:
        if 'round' in row and 'round_name' not in row:
            row['round_name'] = row['round']
    return records


def _latest_records(records: List[Dict]) -> List[Dict]:
    if not records:
        return []
    latest_year = max(int(r.get('year') or 0) for r in records)
    return [r for r in records if int(r.get('year') or 0) == latest_year]


def _contains_any(text: str, words: List[str]) -> bool:
    return any(w in text for w in words)


def _format_money(value) -> str:
    try:
        return f'₹{int(float(value)):,}/year'
    except Exception:
        return 'NA'


def _safe(value, default='NA'):
    return value if value not in [None, ''] else default


def get_student_summary(user) -> Tuple[Dict, str]:
    if not user or not user.is_authenticated:
        return {}, 'No login profile found. Please login and fill the prediction form for profile-based counselling.'
    try:
        profile = StudentProfile.objects.get(user=user)
    except StudentProfile.DoesNotExist:
        return {}, 'Student profile is not completed yet. Please use the Predict page once for personalized suggestions.'

    data = {
        'exam': profile.exam or 'MHT CET',
        'percentile': float(profile.percentile or 0),
        'rank': int(profile.rank or 0),
        'category': profile.category or 'OPEN',
        'home_region': profile.home_region or '',
        'university_quota': profile.university_quota or '',
        'branch': profile.preferred_branch or 'Computer Engineering',
        'city': profile.city_preference or '',
        'max_fees': int(profile.max_fees or 0),
        'aptitude_score': int(profile.aptitude_score or 0),
    }
    summary = (
        f"Profile used: {data['exam']}, percentile {data['percentile']}, rank {data['rank']}, "
        f"category {data['category']}, branch {data['branch']}, quota {data['university_quota'] or 'Any'}, "
        f"city {data['city'] or 'Any'}, aptitude {data['aptitude_score']}"
    )
    return data, summary


def profile_based_recommendation(user, top_n=5) -> str:
    profile_data, summary = get_student_summary(user)
    if not profile_data or profile_data.get('percentile', 0) <= 0:
        return summary + '\n\nTip: Go to Predict page, enter percentile/rank/category/branch once, then chatbot can analyze your exact profile.'

    try:
        results = recommend_colleges(
            percentile=profile_data['percentile'],
            rank=profile_data['rank'],
            exam=profile_data['exam'],
            category=profile_data['category'],
            home_region=profile_data['home_region'],
            university_quota=profile_data['university_quota'],
            branch=profile_data['branch'],
            round_name='CAP Round 1',
            city=profile_data['city'],
            max_fees=profile_data['max_fees'],
            aptitude_score=profile_data['aptitude_score'],
            top_n=top_n,
        )
    except Exception as exc:
        return f'{summary}\n\nCould not generate ML recommendation right now: {exc}'

    if not results:
        return summary + '\n\nNo matching college found. Try relaxing city/fees filters.'

    lines = [summary, '', 'Based on your profile, these colleges look better from current dataset:']
    for idx, row in enumerate(results[:top_n], 1):
        lines.append(
            f"{idx}. {row['college_name']} ({row['city']}) - {row['branch']} | Chance: {row['level']} "
            f"({row['probability']}%) | Previous cutoff: {row['previous_year_closing_percentile']}% | Fees: {_format_money(row['fees_per_year'])}"
        )
    lines.append('\nFor exact final decision, compare CAP round, category, quota, seat matrix and fees.')
    return '\n'.join(lines)


def answer_cutoff_query(question: str, user) -> str:
    records = _latest_records(_dataset_records())
    if not records:
        return 'Dataset is empty. Please load dataset first from Train Model page.'

    profile_data, profile_summary = get_student_summary(user)
    q = question.lower()

    filtered = records
    if profile_data:
        if profile_data.get('exam'):
            filtered = [r for r in filtered if str(r.get('exam', '')).lower() == profile_data['exam'].lower()]
        if profile_data.get('category'):
            filtered = [r for r in filtered if str(r.get('category', '')).upper() == profile_data['category'].upper()]
        if profile_data.get('branch'):
            filtered = [r for r in filtered if str(r.get('branch', '')).lower() == profile_data['branch'].lower()]
        if profile_data.get('city') and ('mumbai' in q or 'pune' in q or 'city' in q or 'location' in q):
            filtered = [r for r in filtered if str(r.get('city', '')).lower() == profile_data['city'].lower()]

    # Detect city from question.
    if 'mumbai' in q:
        filtered = [r for r in filtered if str(r.get('city', '')).lower() == 'mumbai']
    if 'pune' in q:
        filtered = [r for r in filtered if str(r.get('city', '')).lower() == 'pune']

    # Detect branch by matching known branches from dataset.
    branches = sorted({str(r.get('branch', '')) for r in records if r.get('branch')}, key=len, reverse=True)
    for branch in branches:
        if branch and branch.lower() in q:
            filtered = [r for r in filtered if str(r.get('branch', '')).lower() == branch.lower()]
            break

    if not filtered:
        return 'No exact cutoff record found for this query. Try asking with exam, branch, category and city, e.g. Computer Engineering Pune OPEN MHT CET cutoff.'

    filtered = sorted(filtered, key=lambda r: float(r.get('previous_year_closing_percentile') or r.get('closing_percentile') or 0), reverse=True)[:8]
    lines = ['Latest matching cutoff records from dataset:']
    for idx, r in enumerate(filtered, 1):
        lines.append(
            f"{idx}. {_safe(r.get('college_name'))} - {_safe(r.get('branch'))}, {_safe(r.get('city'))}, "
            f"{_safe(r.get('category'))}, {_safe(r.get('exam'))}, {_safe(r.get('round_name') or r.get('round'))}: "
            f"Previous cutoff {_safe(r.get('previous_year_closing_percentile'))}% / rank {_safe(r.get('previous_year_closing_rank'))}; "
            f"3-year trend: {_safe(r.get('cutoff_trend_3yr'))}"
        )
    return '\n'.join(lines)


def answer_ranking_or_fee_query(question: str) -> str:
    records = _latest_records(_dataset_records())
    if not records:
        return 'Dataset is empty. Please load dataset first from Train Model page.'
    q = question.lower()

    if 'mumbai' in q:
        records = [r for r in records if str(r.get('city', '')).lower() == 'mumbai']
    if 'pune' in q:
        records = [r for r in records if str(r.get('city', '')).lower() == 'pune']
    if 'government' in q or 'govt' in q:
        records = [r for r in records if 'govt' in str(r.get('college_type', '')).lower()]
    if 'private' in q:
        records = [r for r in records if 'private' in str(r.get('college_type', '')).lower()]

    # Deduplicate by college.
    unique = {}
    for r in records:
        name = r.get('college_name')
        if name not in unique:
            unique[name] = r
    rows = list(unique.values())

    if _contains_any(q, ['nirf', 'rank', 'ranking', 'top']):
        rows = sorted(rows, key=lambda r: int(r.get('nirf_rank') or 9999))[:8]
        lines = ['Top colleges by NIRF rank from dataset:']
        for idx, r in enumerate(rows, 1):
            lines.append(
                f"{idx}. {_safe(r.get('college_name'))}, {_safe(r.get('city'))} | NIRF: {_safe(r.get('nirf_rank'))} | "
                f"NAAC: {_safe(r.get('naac_grade'))} / {_safe(r.get('naac_score'))} | Type: {_safe(r.get('college_type'))}"
            )
        return '\n'.join(lines)

    if _contains_any(q, ['fee', 'fees', 'low fee', 'budget']):
        rows = sorted(rows, key=lambda r: int(r.get('fees_per_year') or 99999999))[:8]
        lines = ['Lower-fee colleges from dataset:']
        for idx, r in enumerate(rows, 1):
            lines.append(
                f"{idx}. {_safe(r.get('college_name'))}, {_safe(r.get('city'))} | Fees: {_format_money(r.get('fees_per_year'))} | "
                f"Type: {_safe(r.get('college_type'))} | NAAC: {_safe(r.get('naac_grade'))}"
            )
        return '\n'.join(lines)

    rows = sorted(rows, key=lambda r: (-float(r.get('naac_score') or 0), int(r.get('nirf_rank') or 9999)))[:8]
    lines = ['Best colleges by NAAC/NIRF from dataset:']
    for idx, r in enumerate(rows, 1):
        lines.append(
            f"{idx}. {_safe(r.get('college_name'))}, {_safe(r.get('city'))} | NAAC: {_safe(r.get('naac_grade'))}/{_safe(r.get('naac_score'))} | "
            f"NIRF: {_safe(r.get('nirf_rank'))} | Fees: {_format_money(r.get('fees_per_year'))}"
        )
    return '\n'.join(lines)


def answer_chatbot_question(question: str, user=None) -> Dict:
    q = (question or '').strip()
    q_lower = q.lower()

    if not q:
        return {'answer': 'Please type your counselling question.', 'intent': 'empty', 'used_profile': False}

    if _contains_any(q_lower, ['book', 'counsellor', 'counselor', 'human', 'call', 'session', 'appointment']):
        return {
            'answer': (
                'I can hand off this case to a human counsellor. Click “Book Human Counselling” and submit your preferred date/time. '
                'Your latest student profile will be attached automatically.'
            ),
            'intent': 'human_handoff',
            'used_profile': bool(user and user.is_authenticated),
        }

    if _contains_any(q_lower, ['chance', 'recommend', 'suggest', 'profile', 'my percentile', 'my jee', 'my cet', 'better chance', 'admission probability']):
        return {
            'answer': profile_based_recommendation(user),
            'intent': 'profile_recommendation',
            'used_profile': bool(user and user.is_authenticated),
        }

    if _contains_any(q_lower, ['cutoff', 'cut off', 'closing', 'previous year', 'rank', 'trend']):
        return {
            'answer': answer_cutoff_query(q, user),
            'intent': 'historical_cutoff',
            'used_profile': bool(user and user.is_authenticated),
        }

    if _contains_any(q_lower, ['nirf', 'naac', 'rating', 'ranking', 'ranked', 'fees', 'fee', 'budget', 'government', 'govt', 'private', 'top college']):
        return {
            'answer': answer_ranking_or_fee_query(q),
            'intent': 'ranking_fee_filter',
            'used_profile': False,
        }

    if _contains_any(q_lower, ['aptitude', 'psychometric', 'riasec', 'career assessment', 'career suitability']):
        return {
            'answer': (
                'The aptitude module uses RIASEC scoring to identify your career interest pattern. '
                'After the test, it creates a Career Suitability Report and maps recommended branches to the college prediction dataset. '
                'Open the Aptitude Test page and complete the assessment.'
            ),
            'intent': 'aptitude_guidance',
            'used_profile': bool(user and user.is_authenticated),
        }

    if _contains_any(q_lower, ['trending', 'demand index', 'job market', 'salary growth', 'course demand', 'industry course']):
        return {
            'answer': (
                'Trending Course Analysis uses: Demand Index = 0.4 × Job Market Growth + 0.3 × Search Interest Growth + '
                '0.2 × Course Enrollment Growth + 0.1 × Salary Growth. Open the Trending Courses page to compare AI/Data Science, Cyber Security, Cloud/DevOps, VLSI and Robotics.'
            ),
            'intent': 'trending_course_guidance',
            'used_profile': False,
        }

    for key, answer in FAQS.items():
        if key in q_lower:
            return {'answer': answer, 'intent': f'faq_{key}', 'used_profile': False}

    return {
        'answer': (
            'I can help with college recommendations, cutoff trends, previous-year closing cutoff, NAAC/NIRF ranking, fees, '
            'quota/category guidance and CAP counselling FAQs.\n\n'
            'Try asking: “Given my JEE percentile, which Pune colleges are safe?” or “Show previous year cutoff for Computer Engineering in Mumbai.”'
        ),
        'intent': 'fallback',
        'used_profile': False,
    }
