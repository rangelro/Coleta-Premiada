from django.urls import path
from .views import (
    ImovelListCreateView, ImovelDetailView,
    ImovelAddUserView, ImovelRemoveUserView,
    ProgramaListCreateView, ProgramaDetailView,
    ProgramaMaterialsView, ProgramaRulesView,
    ConsolidacaoRunView, ConsolidacaoListView, ConsolidacaoDetailView,
    BeneficioListView, BeneficioDetailView,
    ReportParticipationView, ReportMaterialsView,
    ReportRankingView, ReportImpactView,
)

urlpatterns = [
    # /properties
    path('properties',                 ImovelListCreateView.as_view(), name='imovel-list-create'),
    path('properties/<int:pk>',        ImovelDetailView.as_view(),     name='imovel-detail'),
    path('properties/<int:id>/users',  ImovelAddUserView.as_view(),    name='imovel-add-user'),
    path('properties/<int:id>/users/<int:userId>',
         ImovelRemoveUserView.as_view(), name='imovel-remove-user'),

    # /programs
    path('programs',                   ProgramaListCreateView.as_view(), name='programa-list-create'),
    path('programs/<int:pk>',          ProgramaDetailView.as_view(),     name='programa-detail'),
    path('programs/<int:id>/materials', ProgramaMaterialsView.as_view(), name='programa-materials'),
    path('programs/<int:id>/rules',    ProgramaRulesView.as_view(),      name='programa-rules'),

    # /consolidations
    path('consolidations/run',         ConsolidacaoRunView.as_view(),    name='consolidation-run'),
    path('consolidations',             ConsolidacaoListView.as_view(),   name='consolidation-list'),
    path('consolidations/<int:pk>',    ConsolidacaoDetailView.as_view(), name='consolidation-detail'),

    # /benefits
    path('benefits',                   BeneficioListView.as_view(),   name='benefit-list'),
    path('benefits/<int:propertyId>',  BeneficioDetailView.as_view(), name='benefit-detail'),

    # /reports
    path('reports/participation',      ReportParticipationView.as_view(), name='report-participation'),
    path('reports/materials',          ReportMaterialsView.as_view(),     name='report-materials'),
    path('reports/ranking',            ReportRankingView.as_view(),       name='report-ranking'),
    path('reports/impact',             ReportImpactView.as_view(),        name='report-impact'),
]
