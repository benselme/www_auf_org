# encoding: utf-8

from bs4 import BeautifulSoup
from cms.models.managers import PageManager
from cms.models.pagemodel import Page
from cms.models.pluginmodel import CMSPlugin
from django.conf import settings
from django.utils.translation import string_concat, ugettext_lazy
from haystack import indexes

from project.auf_site_institutionnel.models import \
        Bourse, Actualite, Appel_Offre, Evenement, Publication


class AufIndex(indexes.SearchIndex):
    text = indexes.NgramField(document=True, use_template=True)
    title = indexes.NgramField(model_attr='titre')
    bureaux = indexes.FacetMultiValueField(null=True, stored=True)
    annee = indexes.CharField(faceted=True, stored=True, null=True)
    section = indexes.CharField(faceted=True, stored=True, null=True)

    def prepare_bureaux(self, obj):
        try:
            return [b.nom for b in obj.bureau.all()]
        except ObjectDoesNotExist, e:
            print(e)
            return 'Non précisé'

    def prepare_annee(self, obj):
        if obj.date_pub is not None:
            return str(obj.date_pub.year)


class BourseIndex(AufIndex, indexes.Indexable):

    def get_model(self):
        return Bourse

    def prepare_section(self, obj):
        return ["Bourse"]

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return Bourse.objects.filter(status='3')


class ActualiteIndex(AufIndex, indexes.Indexable):

    def get_model(self):
        return Actualite

    def prepare_section(self, obj):
        return ["Actualité"]

    def index_queryset(self,using=None):
        return Actualite.objects.filter(status='3')


class AppelOffreIndex(AufIndex, indexes.Indexable):
    partenaire = indexes.CharField(faceted=True, stored=True)

    def get_model(self):
        return Appel_Offre

    def prepare_section(self, obj):
        return ["Appel d\'offre"]

    def prepare_partenaire(self, obj):
        if not obj.auf:
            return 'Partenaire'
        else:
            return 'AUF'

    def index_queryset(self, using=None):
        return Appel_Offre.objects.filter(status='3')


class EvenementIndex(AufIndex, indexes.Indexable):

    def get_model(self):
        return Evenement

    def prepare_section(self, obj):
        return ["Événements"]

    def index_queryset(self, using=None):
        return Evenement.objects.filter(status='3')


class PublicationIndex(AufIndex, indexes.Indexable):

    def get_model(self):
        return Publication

    def prepare_section(self, obj):
        return ["Publication"]

    def index_queryset(self, using=None):
        return Publication.objects.filter(status='3')
