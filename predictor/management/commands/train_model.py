from django.core.management.base import BaseCommand
from predictor.ml_utils import train_cutoff_model


class Command(BaseCommand):
    help = 'Train RandomForest models and save model, accuracy, report and confusion matrix.'

    def handle(self, *args, **options):
        metadata = train_cutoff_model()
        self.stdout.write(self.style.SUCCESS('ML models trained and saved successfully.'))
        self.stdout.write('========== TRAINING OUTPUT ==========')
        self.stdout.write(f'Algorithm              : {metadata["algorithm"]}')
        self.stdout.write(f'Dataset rows           : {metadata["dataset_rows"]}')
        self.stdout.write(f'Regression target      : {metadata["target"]}')
        self.stdout.write(f'Classification target  : {metadata["classification_target"]}')
        self.stdout.write(f'MAE percentile points  : {metadata["mae_percentile_points"]}')
        self.stdout.write(f'R2 score               : {metadata["r2_score"]}')
        self.stdout.write(f'Training accuracy      : {metadata["training_accuracy"]}%')
        self.stdout.write(f'Testing accuracy       : {metadata["testing_accuracy"]}%')
        self.stdout.write(f'Years                  : {metadata["years"]}')
        self.stdout.write(f'Exams                  : {metadata["exams"]}')
        self.stdout.write(f'Total colleges         : {len(metadata["colleges"])}')
        self.stdout.write(f'Total branches         : {len(metadata["branches"])}')
        self.stdout.write(f'Total categories       : {len(metadata["categories"])}')
        self.stdout.write('')
        self.stdout.write('========== SAVED FILES ==========')
        self.stdout.write(f'Regression model       : {metadata["regression_model_path"]}')
        self.stdout.write(f'Classifier model       : {metadata["classifier_model_path"]}')
        self.stdout.write(f'Classification report  : {metadata["classification_report_txt"]}')
        self.stdout.write(f'Report CSV             : {metadata["classification_report_csv"]}')
        self.stdout.write(f'Confusion matrix graph : {metadata["confusion_matrix_png"]}')
        self.stdout.write(f'Confusion matrix CSV   : {metadata["confusion_matrix_csv"]}')
        self.stdout.write(f'Training metrics JSON  : {metadata["training_metrics_json"]}')
        self.stdout.write('=================================')
