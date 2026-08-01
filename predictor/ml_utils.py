import json
import math
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from django.conf import settings


def clean_text(value):
    if pd.isna(value):
        return ''
    return str(value).replace('\xa0', ' ').strip()


def clean_upper(value):
    return ' '.join(clean_text(value).upper().split())


def to_float(value, default=0.0):
    try:
        if pd.isna(value) or str(value).strip() == '':
            return default
        return float(str(value).replace('%', '').replace(',', '').strip())
    except Exception:
        return default


def to_int(value, default=0):
    try:
        if pd.isna(value) or str(value).strip() == '':
            return default
        return int(float(str(value).replace(',', '').strip()))
    except Exception:
        return default


def read_raw_dataset(path=None) -> pd.DataFrame:
    path = Path(path or settings.DATASET_PATH)
    if not path.exists():
        raise FileNotFoundError(f'Dataset not found: {path}')
    return pd.read_csv(path, encoding='utf-8-sig')


def prepare_dataset(path=None) -> pd.DataFrame:
    df = read_raw_dataset(path)
    df.columns = [c.strip() for c in df.columns]

    required = [
        'year', 'exam', 'round', 'category', 'home_region', 'university_quota',
        'stream', 'branch', 'college_code', 'college_name', 'college_type',
        'city', 'district', 'state', 'naac_grade', 'naac_score', 'nirf_rank',
        'fees_per_year', 'total_seats', 'category_seats', 'student_percentile',
        'student_rank', 'aptitude_score', 'aptitude_stream_suitability',
        'closing_percentile', 'closing_rank', 'previous_year_closing_percentile',
        'previous_year_closing_rank', 'cutoff_trend_3yr', 'admission_probability'
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f'Missing columns in dataset.csv: {missing}')

    text_cols = [
        'exam', 'round', 'home_region', 'university_quota', 'stream', 'branch',
        'college_code', 'college_name', 'college_type', 'city', 'district', 'state',
        'naac_grade', 'aptitude_stream_suitability', 'cutoff_trend_3yr', 'admission_probability'
    ]
    for col in text_cols:
        df[col] = df[col].apply(lambda x: ' '.join(clean_text(x).split()))
    df['category'] = df['category'].apply(clean_upper)

    int_cols = ['record_id', 'year', 'nirf_rank', 'fees_per_year', 'total_seats', 'category_seats', 'student_rank', 'aptitude_score', 'closing_rank', 'previous_year_closing_rank']
    for col in int_cols:
        if col in df.columns:
            df[col] = df[col].apply(to_int)

    float_cols = ['naac_score', 'student_percentile', 'closing_percentile', 'previous_year_closing_percentile']
    for col in float_cols:
        df[col] = df[col].apply(to_float)

    df = df[(df['closing_percentile'] >= 0) & (df['closing_percentile'] <= 100)]
    df = df.drop_duplicates()
    return df


# Backward-compatible name used by older views/commands.
def prepare_long_dataset(path=None) -> pd.DataFrame:
    return prepare_dataset(path)


def _uniq(df, col):
    return sorted([str(x) for x in df[col].dropna().unique().tolist() if str(x).strip()])


def get_dataset_options() -> Dict[str, List[str]]:
    try:
        df = prepare_dataset()
        return {
            'exams': _uniq(df, 'exam'),
            'categories': _uniq(df, 'category'),
            'home_regions': _uniq(df, 'home_region'),
            'university_quotas': _uniq(df, 'university_quota'),
            'branches': _uniq(df, 'branch'),
            'rounds': _uniq(df, 'round'),
            'cities': _uniq(df, 'city'),
            'college_types': _uniq(df, 'college_type'),
        }
    except Exception:
        return {
            'exams': ['MHT CET', 'JEE'],
            'categories': ['OPEN', 'OBC', 'SC', 'ST', 'EWS', 'VJNT'],
            'home_regions': ['Mumbai University', 'Pune University'],
            'university_quotas': ['Home University', 'Other University', 'All India'],
            'branches': ['Computer Engineering', 'Information Technology', 'Mechanical Engineering'],
            'rounds': ['CAP Round 1', 'CAP Round 2', 'CAP Round 3'],
            'cities': ['Mumbai', 'Pune'],
            'college_types': ['Govt', 'Private'],
        }


def feature_columns() -> List[str]:
    return [
        'year', 'exam', 'round', 'category', 'home_region', 'university_quota',
        'branch', 'college_name', 'college_type', 'city', 'naac_score', 'nirf_rank',
        'fees_per_year', 'total_seats', 'category_seats',
        'previous_year_closing_percentile', 'previous_year_closing_rank'
    ]



def classification_feature_columns() -> List[str]:
    """Features used to train admission probability classifier."""
    return feature_columns() + [
        'student_percentile', 'student_rank', 'aptitude_score'
    ]


def _ensure_report_dirs() -> Dict[str, Path]:
    report_dir = Path(getattr(settings, 'REPORT_DIR', settings.BASE_DIR / 'training_reports'))
    static_report_dir = settings.BASE_DIR / 'predictor' / 'static' / 'predictor' / 'reports'
    report_dir.mkdir(parents=True, exist_ok=True)
    static_report_dir.mkdir(parents=True, exist_ok=True)
    return {'report_dir': report_dir, 'static_report_dir': static_report_dir}


def _save_confusion_matrix_image(cm, labels, output_path: Path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from sklearn.metrics import ConfusionMatrixDisplay

    fig, ax = plt.subplots(figsize=(7, 6))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=labels)
    disp.plot(ax=ax, values_format='d')
    ax.set_title('Admission Probability Confusion Matrix')
    plt.tight_layout()
    fig.savefig(output_path, dpi=160, bbox_inches='tight')
    plt.close(fig)


def train_cutoff_model(path=None, model_path=None, metadata_path=None) -> Dict:
    """Train both models and save model + reports.

    1) RandomForestRegressor predicts closing_percentile/cutoff.
    2) RandomForestClassifier predicts admission_probability: High/Medium/Low.

    Saved outputs:
    - ml_models/college_cutoff_model.joblib
    - ml_models/college_probability_classifier.joblib
    - training_reports/classification_report.txt
    - training_reports/classification_report.csv
    - training_reports/confusion_matrix.png
    - training_reports/confusion_matrix.csv
    - training_reports/training_metrics.json
    """
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    from sklearn.metrics import (
        accuracy_score,
        classification_report,
        confusion_matrix,
        mean_absolute_error,
        r2_score,
    )
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder

    df = prepare_dataset(path)
    report_dirs = _ensure_report_dirs()
    report_dir = report_dirs['report_dir']
    static_report_dir = report_dirs['static_report_dir']

    # =========================
    # 1) Regression model
    # =========================
    regression_features = feature_columns()
    regression_target = 'closing_percentile'

    X = df[regression_features]
    y = df[regression_target]

    reg_cat_cols = [
        'exam', 'round', 'category', 'home_region', 'university_quota',
        'branch', 'college_name', 'college_type', 'city'
    ]
    reg_num_cols = [
        'year', 'naac_score', 'nirf_rank', 'fees_per_year', 'total_seats',
        'category_seats', 'previous_year_closing_percentile',
        'previous_year_closing_rank'
    ]

    reg_preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore'), reg_cat_cols),
            ('num', 'passthrough', reg_num_cols),
        ]
    )
    reg_model = RandomForestRegressor(
        n_estimators=300,
        random_state=42,
        max_depth=22,
        min_samples_leaf=2,
        n_jobs=-1,
    )
    reg_pipeline = Pipeline(steps=[('preprocessor', reg_preprocessor), ('model', reg_model)])

    if len(df) > 20:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
    else:
        X_train, X_test, y_train, y_test = X, X, y, y

    reg_pipeline.fit(X_train, y_train)
    reg_preds = reg_pipeline.predict(X_test)
    mae = float(mean_absolute_error(y_test, reg_preds))
    r2 = float(r2_score(y_test, reg_preds)) if len(y_test) > 1 else 1.0

    model_path = Path(model_path or settings.MODEL_PATH)
    metadata_path = Path(metadata_path or settings.METADATA_PATH)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(reg_pipeline, model_path)

    # =========================
    # 2) Classification model
    # =========================
    clf_features = classification_feature_columns()
    clf_target = 'admission_probability'

    clf_df = df.copy()
    clf_df[clf_target] = clf_df[clf_target].apply(lambda x: clean_text(x).title())
    clf_df = clf_df[clf_df[clf_target].isin(['High', 'Medium', 'Low'])]
    if clf_df.empty:
        raise ValueError('No valid High/Medium/Low values found in admission_probability column.')

    Xc = clf_df[clf_features]
    yc = clf_df[clf_target]

    clf_cat_cols = reg_cat_cols
    clf_num_cols = reg_num_cols + ['student_percentile', 'student_rank', 'aptitude_score']

    clf_preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore'), clf_cat_cols),
            ('num', 'passthrough', clf_num_cols),
        ]
    )
    clf_model = RandomForestClassifier(
        n_estimators=300,
        random_state=42,
        max_depth=22,
        min_samples_leaf=2,
        class_weight='balanced',
        n_jobs=-1,
    )
    clf_pipeline = Pipeline(steps=[('preprocessor', clf_preprocessor), ('model', clf_model)])

    class_counts = yc.value_counts()
    can_stratify = len(class_counts) > 1 and class_counts.min() >= 2 and len(clf_df) > 20
    stratify = yc if can_stratify else None

    if len(clf_df) > 20:
        Xc_train, Xc_test, yc_train, yc_test = train_test_split(
            Xc, yc, test_size=0.2, random_state=42, stratify=stratify
        )
    else:
        Xc_train, Xc_test, yc_train, yc_test = Xc, Xc, yc, yc

    clf_pipeline.fit(Xc_train, yc_train)
    train_pred = clf_pipeline.predict(Xc_train)
    test_pred = clf_pipeline.predict(Xc_test)

    train_accuracy = float(accuracy_score(yc_train, train_pred))
    test_accuracy = float(accuracy_score(yc_test, test_pred))
    labels = [label for label in ['High', 'Medium', 'Low'] if label in sorted(yc.unique())]

    report_text = classification_report(
        yc_test,
        test_pred,
        labels=labels,
        zero_division=0,
    )
    report_dict = classification_report(
        yc_test,
        test_pred,
        labels=labels,
        output_dict=True,
        zero_division=0,
    )
    cm = confusion_matrix(yc_test, test_pred, labels=labels)

    classifier_model_path = Path(getattr(settings, 'CLASSIFIER_MODEL_PATH', model_path.parent / 'college_probability_classifier.joblib'))
    classifier_model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf_pipeline, classifier_model_path)

    classification_report_txt = report_dir / 'classification_report.txt'
    classification_report_csv = report_dir / 'classification_report.csv'
    confusion_matrix_csv = report_dir / 'confusion_matrix.csv'
    confusion_matrix_png = report_dir / 'confusion_matrix.png'
    confusion_matrix_static_png = static_report_dir / 'confusion_matrix.png'
    training_metrics_json = report_dir / 'training_metrics.json'

    classification_report_txt.write_text(report_text, encoding='utf-8')
    pd.DataFrame(report_dict).transpose().to_csv(classification_report_csv, encoding='utf-8-sig')
    pd.DataFrame(cm, index=labels, columns=labels).to_csv(confusion_matrix_csv, encoding='utf-8-sig')
    _save_confusion_matrix_image(cm, labels, confusion_matrix_png)
    _save_confusion_matrix_image(cm, labels, confusion_matrix_static_png)

    training_metrics = {
        'classifier_algorithm': 'RandomForestClassifier',
        'classification_target': clf_target,
        'training_accuracy': round(train_accuracy * 100, 2),
        'testing_accuracy': round(test_accuracy * 100, 2),
        'classes': labels,
        'classification_report_txt': str(classification_report_txt),
        'classification_report_csv': str(classification_report_csv),
        'confusion_matrix_png': str(confusion_matrix_png),
        'confusion_matrix_csv': str(confusion_matrix_csv),
    }
    training_metrics_json.write_text(json.dumps(training_metrics, indent=2), encoding='utf-8')

    metadata = {
        'algorithm': 'RandomForestRegressor + RandomForestClassifier',
        'regression_algorithm': 'RandomForestRegressor',
        'classifier_algorithm': 'RandomForestClassifier',
        'dataset_rows': int(len(df)),
        'features': regression_features,
        'classification_features': clf_features,
        'target': regression_target,
        'classification_target': clf_target,
        'mae_percentile_points': round(mae, 4),
        'r2_score': round(r2, 4),
        'training_accuracy': round(train_accuracy * 100, 2),
        'testing_accuracy': round(test_accuracy * 100, 2),
        'years': sorted(df['year'].unique().astype(int).tolist()),
        'exams': _uniq(df, 'exam'),
        'categories': _uniq(df, 'category'),
        'branches': _uniq(df, 'branch'),
        'cities': _uniq(df, 'city'),
        'college_types': _uniq(df, 'college_type'),
        'colleges': _uniq(df, 'college_name'),
        'regression_model_path': str(model_path),
        'classifier_model_path': str(classifier_model_path),
        'classification_report_txt': str(classification_report_txt),
        'classification_report_csv': str(classification_report_csv),
        'confusion_matrix_png': str(confusion_matrix_png),
        'confusion_matrix_csv': str(confusion_matrix_csv),
        'training_metrics_json': str(training_metrics_json),
        'confusion_matrix_static_url': 'predictor/reports/confusion_matrix.png',
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    return metadata

def load_model():
    model_path = Path(settings.MODEL_PATH)
    if not model_path.exists():
        train_cutoff_model()
    return joblib.load(model_path)


def admission_probability(student_percentile: float, predicted_cutoff: float, previous_cutoff: float = 0, aptitude_score: int = 0) -> Tuple[float, str, str]:
    """Weighted probability using current model cutoff, previous year cutoff, and aptitude score."""
    student_percentile = float(student_percentile)
    predicted_cutoff = float(predicted_cutoff)
    previous_cutoff = float(previous_cutoff or predicted_cutoff)
    aptitude_score = int(aptitude_score or 0)

    current_margin = student_percentile - predicted_cutoff
    previous_margin = student_percentile - previous_cutoff
    aptitude_bonus = (aptitude_score - 50) / 20.0  # -2.5 to +2.5 approx
    weighted_margin = (0.60 * current_margin) + (0.30 * previous_margin) + (0.10 * aptitude_bonus)

    probability = 100.0 / (1.0 + math.exp(-(weighted_margin / 5.0)))
    if weighted_margin >= 5:
        level, badge = 'High', 'success'
    elif weighted_margin >= -3:
        level, badge = 'Medium', 'warning'
    else:
        level, badge = 'Low', 'danger'
    return round(probability, 2), level, badge


def recommend_colleges(
    percentile: float,
    category: str,
    branch: str,
    exam: str = 'MHT CET',
    round_name: str = 'CAP Round 1',
    rank: int = 0,
    home_region: str = '',
    university_quota: str = '',
    city: str = '',
    college_type: str = '',
    max_fees: int = 0,
    min_naac_score: float = 0,
    max_nirf_rank: int = 0,
    aptitude_score: int = 0,
    top_n: int = 30,
) -> List[Dict]:
    df = prepare_dataset()
    model = load_model()

    category = clean_upper(category)
    branch = clean_text(branch)
    exam = clean_text(exam)
    round_name = clean_text(round_name)
    home_region = clean_text(home_region)
    university_quota = clean_text(university_quota)
    city = clean_text(city)
    college_type = clean_text(college_type)
    max_fees = int(max_fees or 0)
    max_nirf_rank = int(max_nirf_rank or 0)
    min_naac_score = float(min_naac_score or 0)

    candidates = df.copy()
    # Hard filters from FR2/FR3.
    candidates = candidates[candidates['exam'] == exam]
    candidates = candidates[candidates['branch'] == branch]
    candidates = candidates[candidates['category'] == category]
    candidates = candidates[candidates['round'] == round_name]
    if home_region:
        candidates = candidates[candidates['home_region'] == home_region]
    if university_quota:
        candidates = candidates[candidates['university_quota'] == university_quota]
    if city:
        candidates = candidates[candidates['city'] == city]
    if college_type:
        candidates = candidates[candidates['college_type'] == college_type]
    if max_fees:
        candidates = candidates[candidates['fees_per_year'] <= max_fees]
    if min_naac_score:
        candidates = candidates[candidates['naac_score'] >= min_naac_score]
    if max_nirf_rank:
        candidates = candidates[candidates['nirf_rank'] <= max_nirf_rank]

    # Fallbacks to avoid blank output if user selects a rare combination.
    if candidates.empty:
        candidates = df[(df['exam'] == exam) & (df['branch'] == branch) & (df['category'] == category)].copy()
    if candidates.empty:
        candidates = df[(df['exam'] == exam) & (df['branch'] == branch)].copy()
    if candidates.empty:
        candidates = df[df['branch'] == branch].copy()
    if candidates.empty:
        candidates = df.copy()

    latest_year = int(candidates['year'].max())
    candidates = candidates[candidates['year'] == latest_year].copy()
    candidates = candidates.drop_duplicates(subset=['college_code', 'college_name', 'branch', 'category', 'exam', 'round'])

    # Predict expected current closing percentile for selected student context.
    predict_rows = candidates.copy()
    predict_rows['exam'] = exam
    predict_rows['round'] = round_name
    predict_rows['category'] = category
    predict_rows['branch'] = branch
    if home_region:
        predict_rows['home_region'] = home_region
    if university_quota:
        predict_rows['university_quota'] = university_quota

    X = predict_rows[feature_columns()]
    predicted = model.predict(X)

    rows = []
    for record, pred_cutoff in zip(predict_rows.to_dict('records'), predicted):
        pred_cutoff = max(0.0, min(100.0, float(pred_cutoff)))
        previous_cutoff = float(record.get('previous_year_closing_percentile') or 0)
        probability, level, badge = admission_probability(percentile, pred_cutoff, previous_cutoff, aptitude_score)
        margin = round(float(percentile) - pred_cutoff, 2)
        rows.append({
            'college_code': record.get('college_code', ''),
            'college_name': record.get('college_name', ''),
            'college_type': record.get('college_type', ''),
            'city': record.get('city', ''),
            'district': record.get('district', ''),
            'exam': exam,
            'round_name': round_name,
            'category': category,
            'home_region': record.get('home_region', ''),
            'university_quota': record.get('university_quota', ''),
            'branch': branch,
            'naac_grade': record.get('naac_grade', ''),
            'naac_score': round(float(record.get('naac_score') or 0), 2),
            'nirf_rank': int(record.get('nirf_rank') or 0),
            'fees_per_year': int(record.get('fees_per_year') or 0),
            'total_seats': int(record.get('total_seats') or 0),
            'category_seats': int(record.get('category_seats') or 0),
            'student_percentile': round(float(percentile), 2),
            'student_rank': int(rank or 0),
            'aptitude_score': int(aptitude_score or 0),
            'actual_closing_percentile': round(float(record.get('closing_percentile') or 0), 2),
            'actual_closing_rank': int(record.get('closing_rank') or 0),
            'previous_year_closing_percentile': round(previous_cutoff, 2),
            'previous_year_closing_rank': int(record.get('previous_year_closing_rank') or 0),
            'cutoff_trend_3yr': record.get('cutoff_trend_3yr', ''),
            'predicted_cutoff': round(pred_cutoff, 2),
            'margin': margin,
            'probability': probability,
            'level': level,
            'badge': badge,
        })

    rows = sorted(rows, key=lambda x: (x['probability'], x['naac_score'], -x['nirf_rank']), reverse=True)
    return rows[: int(top_n)]


def load_metadata() -> Dict:
    path = Path(settings.METADATA_PATH)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))
