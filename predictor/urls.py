from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('predict/', views.predict, name='predict'),
    path('history/', views.history, name='history'),
    path('train/', views.train_model_view, name='train_model_view'),
    path('load-dataset/', views.load_dataset_view, name='load_dataset_view'),

    # FR4 Chatbot counselling
    path('chatbot/', views.chatbot, name='chatbot'),

    # FR5 Human counselling services
    path('counsellors/', views.counsellors, name='counsellors'),
    path('book-counselling/', views.book_counselling, name='book_counselling'),
    path('book-counselling/<int:counsellor_id>/', views.book_counselling, name='book_counselling_with_counsellor'),
    path('payment/<int:session_id>/', views.payment_checkout, name='payment_checkout'),
    path('my-counselling-sessions/', views.my_counselling_sessions, name='my_counselling_sessions'),
    path('counsellor-dashboard/', views.counsellor_dashboard, name='counsellor_dashboard'),

    # FR6 Aptitude and career assessment
    path('aptitude-test/', views.aptitude_test, name='aptitude_test'),
    path('aptitude-result/', views.aptitude_result, name='latest_aptitude_result'),
    path('aptitude-result/<int:result_id>/', views.aptitude_result, name='aptitude_result'),

    # FR7 Trending industry course analysis
    path('trending-courses/', views.trending_courses, name='trending_courses'),
]
