# -*- encoding: utf-8 -*-
import datetime
from django.conf import settings
from django.core.mail.message import EmailMessage

from django.template import RequestContext
from django.shortcuts import render_to_response
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect
from django.forms.models import modelformset_factory
from django.forms.models import model_to_dict

from project.espace_membre import models
from project.espace_membre.decorators import membre_connecte
from project.espace_membre import forms


def accueil(request):
    c = {
        'erreur': request.session.get('espace_membre_erreur', False)
    }
    if request.method == "POST" and 'token' in request.POST:
        try:
            return verifier_token(request, request.POST['token'])
        except ObjectDoesNotExist:
            c['erreur'] = True

    # si erreur, on clear la session
    if c['erreur']:
        try:
            request.session['espace_membre_erreur'] = None
        except KeyError:
            pass
        try:
            request.session['espace_membre_etablissement'] = False
        except KeyError:
            pass

    return render_to_response('espace_membre/accueil.html', c, RequestContext(request))


def connexion(request, token):
    try:
        return verifier_token(request, token)
    except ObjectDoesNotExist:
        request.session['espace_membre_erreur'] = True
        return redirect('espace_membre_accueil')


@membre_connecte
def apercu(request):
    e = models.EtablissementModification.objects \
        .get(etablissement=request.session['espace_membre_etablissement'])
    print e.validation_etablissement
    #form = forms.EtablissementForm(None, instance=e)

    formset_pha, formset_com = construire_formset(request)

    form = forms.EtablissementForm(request.POST or None, instance=e)

    c = {
        'form': form,
        'formset_pha': formset_pha,
        'formset_com': formset_com,
        'etablissement': e,
        'ESPACE_MEMBRE_SENDER': settings.ESPACE_MEMBRE_SENDER,
    }
    return render_to_response('espace_membre/apercu.html', c, RequestContext(request))


@membre_connecte
def modifier(request):
    e = models.EtablissementModification.objects \
        .get(etablissement=request.session['espace_membre_etablissement'])
    if e.validation_etablissement:
        return redirect('espace_membre_apercu')

    formset_pha, formset_com = construire_formset(request)

    form = forms.EtablissementForm(request.POST or None, instance=e)

    erreur = False
    # on contourne l'évaluation booléenne partielle car on veut que tous les
    # is_valid soient appelés, pour que les champs invalides soient stylés
    # correctement
    valid = form.is_valid()
    com_valid = formset_com.is_valid()
    pha_valid = formset_pha.is_valid()
    if valid and com_valid and pha_valid:
        form.save()
        for f in formset_com.save(commit=False):
            f.etablissement = e
            f.type = "c"
            f.modification_par = u"Établissement"
            f.save()
        # on limite à un PHA
        saved_forms = formset_pha.save(commit=False)
        try:
            f = saved_forms[0]
            f.etablissement = e
            f.type = "r"
            f.modification_par = u"Établissement"
            f.save()
        except IndexError:
            pass
        return redirect('espace_membre_apercu')
    elif request.method == "POST":
        # on POST, donc quelque chose n'est pas valide
        erreur = True

    c = {
        'form': form,
        'formset_com': formset_com,
        'formset_pha': formset_pha,
        'erreur': erreur,
        'ESPACE_MEMBRE_SENDER': settings.ESPACE_MEMBRE_SENDER,
    }

    return render_to_response('espace_membre/modifier.html', c, RequestContext(request))


@membre_connecte
def valider(request):
    e = models.EtablissementModification.objects \
        .get(etablissement=request.session['espace_membre_etablissement'])
    if not e.validation_etablissement:
        e.validation_etablissement = True
        e.date_validation_etablissement = datetime.date.today()
        e.set_flags_a_valider()
        e.save()
        message = EmailMessage(u"Validation des données",
                               u"L''établissement %s(%s) a validé ses données." % (
                                   e.nom, e.id),
                               # adresse de retour
                               settings.ESPACE_MEMBRE_SENDER,
                               # adresses des destinataires
                               [admin[1]
                                   for admin in settings.ESPACE_MEMBRE_ADMINS]
                               )
        message.send(fail_silently=True)

    return redirect('espace_membre_apercu')


def verifier_token(request, token):
    """ Vérifie si le token est valide et redirege l'usager """
    token = models.Acces.objects.select_related('etablissement') \
        .get(token=token)

    request.session['espace_membre_etablissement'] = token.etablissement_id
    if not models.EtablissementModification.objects.filter(
            etablissement=token.etablissement).count():
        e = models.EtablissementModification()
        e_dict = model_to_dict(token.etablissement)
        e_dict['etablissement_id'] = e_dict['id']
        del e_dict['id']
        for key, value in e_dict.items():
            try:
                setattr(e, key, value)
            except ValueError:
                setattr(e, "%s_id" % key, value)
        e.publication_electronique = True
        e.publication_papier = True
        e.save()
        for f in e.get_responsables_set().exclude(
                id__in=[
                    r.responsable_id for r in
                    e.get_responsables_modification_set().all()]
        ):
            f_dict = model_to_dict(f)
            f_dict['responsable_id'] = f_dict['id']
            f_dict['etablissement_id'] = e.id
            del f_dict['id']
            del f_dict['etablissement']
            new_f = models.ResponsableModification()
            for key, value in f_dict.items():
                setattr(new_f, key, value)
            new_f.save()

    else:
        e = models.EtablissementModification.objects.get(
            etablissement=token.etablissement)
        if e.validation_etablissement:
            return redirect('espace_membre_apercu')

    return redirect('espace_membre_modifier')


def construire_formset(request):
    assert('espace_membre_etablissement' in request.session)
    e = models.EtablissementModification.objects \
        .get(etablissement=request.session['espace_membre_etablissement'])

    if len(e.get_responsables_set()) != \
            len(e.get_responsables_modification_set()):
        pass

    ResponsableFormset = modelformset_factory(
        models.ResponsableModification, forms.ResponsableForm, extra=0,
        can_delete=False, formset=forms.RequiredFormSet)
    ResponsableFormsetCom = modelformset_factory(
        models.ResponsableModification, forms.ResponsableCommunicationForm,
        extra=1, max_num=1, can_delete=False, formset=forms.RequiredFormSet)

    formset_com = ResponsableFormsetCom(
        request.POST or None,
        queryset=e.get_responsables_modification_com(), prefix='com'
    )
    formset_pha = ResponsableFormset(
        request.POST or None,
        queryset=e.get_responsables_modification_pha(), prefix='pha'
    )

    return formset_pha, formset_com
