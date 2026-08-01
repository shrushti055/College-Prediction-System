from django.core.management.base import BaseCommand
from predictor.models import CollegeCutoff
from predictor.ml_utils import prepare_dataset


class Command(BaseCommand):
    help = 'Load data/dataset.csv into SQLite CollegeCutoff table.'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Clear existing rows before loading')

    def handle(self, *args, **options):
        if options['clear']:
            deleted, _ = CollegeCutoff.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Deleted existing rows: {deleted}'))

        df = prepare_dataset()
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
        self.stdout.write(self.style.SUCCESS('Dataset loaded successfully into SQLite.'))
        self.stdout.write(f'Rows inserted       : {len(objects)}')
        self.stdout.write(f'Colleges            : {df["college_name"].nunique()}')
        self.stdout.write(f'Branches            : {df["branch"].nunique()}')
        self.stdout.write(f'Exams               : {", ".join(sorted(df["exam"].unique()))}')
        self.stdout.write(f'Cities              : {", ".join(sorted(df["city"].unique()))}')
        self.stdout.write(f'Years               : {", ".join(map(str, sorted(df["year"].unique())))}')
