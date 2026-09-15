import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    Cria (ou atualiza a senha de) um superusuário a partir de variáveis
    de ambiente, de forma idempotente e não interativa.

    Motivação: o plano gratuito do Render não inclui acesso a Shell
    interativo, então não é possível rodar `createsuperuser` (que pede
    input do teclado) manualmente após o deploy. Este comando roda
    automaticamente a cada build (ver build.sh) e:

    - não faz nada se as variáveis de ambiente não estiverem definidas;
    - cria o usuário se ele ainda não existir;
    - se já existir, apenas garante que ele continua superusuário/staff
      (não sobrescreve a senha de um usuário já existente, para não
      resetar a senha do professor sem querer a cada deploy).

    Variáveis de ambiente esperadas:
      DJANGO_SUPERUSER_USERNAME
      DJANGO_SUPERUSER_PASSWORD
      DJANGO_SUPERUSER_EMAIL (opcional)
    """

    help = "Cria um superusuário a partir de variáveis de ambiente (uso em deploy sem shell)."

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")

        if not username or not password:
            self.stdout.write(
                "DJANGO_SUPERUSER_USERNAME/PASSWORD não definidos — nenhum superusuário criado."
            )
            return

        User = get_user_model()
        usuario, criado = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "is_staff": True, "is_superuser": True},
        )

        if criado:
            usuario.set_password(password)
            usuario.save()
            self.stdout.write(self.style.SUCCESS(f"Superusuário '{username}' criado com sucesso."))
        else:
            alterado = False
            if not usuario.is_superuser or not usuario.is_staff:
                usuario.is_superuser = True
                usuario.is_staff = True
                alterado = True
            if alterado:
                usuario.save()
            self.stdout.write(f"Superusuário '{username}' já existia — nada foi alterado.")
