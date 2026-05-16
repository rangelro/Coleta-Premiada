from django.db import models
from auditlog.registry import auditlog
# Create your models here.


from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models


class UsuarioManager(BaseUserManager):
    def create_user(self, email, password=None, **extras):
        if not email:
            raise ValueError('E-mail obrigatório')
        email = self.normalize_email(email)
        user  = self.model(email=email, **extras)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extras):
        extras.setdefault('is_staff', True)
        extras.setdefault('is_superuser', True)
        return self.create_user(email, password, **extras)


class Usuario(AbstractBaseUser, PermissionsMixin):
    PERFIS = [
        ('supervisor','Supervisor'),
        ('morador','Morador'),
        ('gestor','Gestor')
    ]

    email    = models.EmailField(unique=True)
    cpf      = models.CharField(max_length=14, unique=True)
    nome     = models.CharField(max_length=150)
    perfil   = models.CharField(max_length=20, choices=PERFIS)
    ativo    = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects  = UsuarioManager()

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['cpf', 'nome', 'perfil']

    def __str__(self):
        return f"{self.nome} ({self.perfil})"
    
auditlog.register(Usuario)