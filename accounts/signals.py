from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Professor


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def criar_professor_para_novo_usuario(sender, instance, created, **kwargs):
    """Garante que todo usuário autenticado tenha um perfil de Professor."""
    if created:
        Professor.objects.get_or_create(user=instance)
