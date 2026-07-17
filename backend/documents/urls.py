from django.urls import path
from .views import DocumentListView, DocumentUploadView, DocumentCollectionListCreateView

urlpatterns = [
    path('', DocumentListView.as_view(), name='document-list'),
    path('upload/', DocumentUploadView.as_view(), name='document-upload'),
    path('collections/', DocumentCollectionListCreateView.as_view(), name='collection-list-create'),
]
