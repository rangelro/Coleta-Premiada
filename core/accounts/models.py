from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
import secrets
from django.utils import timezone


class UsuarioManager(BaseUserManager):
    def create_user(self, email, password=None, **extras):
        if not email:
            raise ValueError('E-mail obrigatório')
        email = self.normalize_email(email)
        user = self.model(email=email, **extras)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extras):
        extras.setdefault('is_staff', True)
        extras.setdefault('is_superuser', True)
        extras.setdefault('perfil', 'gestor')
        return self.create_user(email, password, **extras)


class Role(models.Model):
    """
    Permissão/Papel customizado atribuível a um usuário.

    Diferente do `perfil` (que define o tipo do usuário no domínio),
    Role representa permissões granulares definidas pelo gestor.
    """
    nome = models.CharField(max_length=80, unique=True)
    descricao = models.CharField(max_length=255, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Cidade(models.Model):
    """
    Cidade atendida pelo sistema.

    Gestor e supervisor pertencem a exatamente uma cidade (Usuario.cidade).
    O morador não tem cidade própria: ela é escolhida por imóvel
    (ver `program.Imovel.cidade`, validado contra este catálogo).
    """
    nome = models.CharField(max_length=100, unique=True)
    uf = models.CharField(max_length=2, help_text='Sigla do estado (UF)')
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nome']
        verbose_name_plural = 'cidades'

    def __str__(self):
        return f"{self.nome}/{self.uf}"


class Usuario(AbstractBaseUser, PermissionsMixin):
    PERFIS = [
        ('supervisor', 'Supervisor'),
        ('morador', 'Morador'),
        ('gestor', 'Gestor'),
        ('gerente_geral', 'Gerente Geral'),
    ]

    # Perfis que pertencem a exatamente uma cidade.
    PERFIS_COM_CIDADE_OBRIGATORIA = ('gestor', 'supervisor')

    email = models.EmailField(unique=True)
    cpf = models.CharField(max_length=14, unique=True, null=True, blank=True)
    matricula = models.CharField(max_length=20, unique=True, null=True, blank=True)
    nome = models.CharField(max_length=150)
    sobrenome = models.CharField(max_length=100, blank=True, default='')
    perfil = models.CharField(max_length=20, choices=PERFIS)
    cadastro_completo = models.BooleanField(
        default=True,
        help_text='False apenas para moradores que se cadastraram via Google e ainda não preencheram o formulário complementar.',
    )
    cidade = models.ForeignKey(
        Cidade,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='usuarios',
        help_text='Obrigatória para gestor e supervisor; gerente_geral e morador não têm cidade própria.',
    )
    ativo = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    roles = models.ManyToManyField(Role, blank=True, related_name='usuarios')
    email_confirmado = models.BooleanField(default=False)
    token_confirmacao = models.CharField(max_length=64, blank=True, null=True, unique=True)
    token_expira_em = models.DateTimeField(null=True, blank=True)

    objects = UsuarioManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nome', 'perfil']

    def clean(self):
        super().clean()
        if self.perfil in self.PERFIS_COM_CIDADE_OBRIGATORIA and not self.cidade_id:
            raise ValidationError({'cidade': 'Cidade obrigatória para o perfil informado.'})

    def __str__(self):
        return f"{self.nome} ({self.perfil})"
