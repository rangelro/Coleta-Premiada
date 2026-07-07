from django.urls import path
from .views import (
    ImovelListCreateView, ImovelDetailView,
    ImovelAddUserView, ImovelRemoveUserView,
    ProgramaListCreateView, ProgramaDetailView,
    ProgramaRulesView,
    ConsolidacaoRunView, ConsolidacaoListView, ConsolidacaoDetailView,
    BeneficioListView, BeneficioDetailView,
    ReportParticipationView,
    ReportRankingView, ReportImpactView,
    ConstantePontuacaoView,
)

urlpatterns = [
    # /properties
    path('properties',                 ImovelListCreateView.as_view(), name='imovel-list-create'),
    path('properties/<str:pk>',        ImovelDetailView.as_view(),     name='imovel-detail'),
    path('properties/<str:id>/users',  ImovelAddUserView.as_view(),    name='imovel-add-user'),
    path('properties/<str:id>/users/<int:userId>',
         ImovelRemoveUserView.as_view(), name='imovel-remove-user'),

    # /programs
    path('programs',                   ProgramaListCreateView.as_view(), name='programa-list-create'),
    path('programs/<int:pk>',          ProgramaDetailView.as_view(),     name='programa-detail'),
    path('programs/<int:id>/rules',    ProgramaRulesView.as_view(),      name='programa-rules'),

    # /consolidations
    path('consolidations/run',         ConsolidacaoRunView.as_view(),    name='consolidation-run'),
    path('consolidations',             ConsolidacaoListView.as_view(),   name='consolidation-list'),
    path('consolidations/<int:pk>',    ConsolidacaoDetailView.as_view(), name='consolidation-detail'),

    # /benefits
    path('benefits',                   BeneficioListView.as_view(),   name='benefit-list'),
    path('benefits/<int:propertyId>/<int:programaId>', BeneficioDetailView.as_view(), name='benefit-detail'),

    # /reports
    path('reports/participation',      ReportParticipationView.as_view(), name='report-participation'),
    path('reports/ranking',            ReportRankingView.as_view(),       name='report-ranking'),
    path('reports/impact',             ReportImpactView.as_view(),        name='report-impact'),

    # /scoring-constant
    path('scoring-constant',           ConstantePontuacaoView.as_view(),  name='scoring-constant'),
]
