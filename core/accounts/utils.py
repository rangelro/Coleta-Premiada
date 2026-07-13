import secrets
from django.utils import timezone
from datetime import timedelta


def gerar_token_confirmacao(usuario):
    token = secrets.token_urlsafe(48)
    usuario.token_confirmacao = token
    usuario.token_expira_em = timezone.now() + timedelta(hours=24)
    usuario.save(update_fields=['token_confirmacao', 'token_expira_em'])
    return token


def validar_cpf(cpf: str) -> bool:
    """Valida CPF brasileiro pelo algoritmo Módulo 11."""
    digits = ''.join(c for c in cpf if c.isdigit())
    if len(digits) != 11 or len(set(digits)) == 1:
        return False
    for i, mult_start in enumerate([10, 11]):
        soma = sum(int(digits[j]) * (mult_start - j) for j in range(mult_start - 1))
        resto = soma % 11
        expected = 0 if resto < 2 else 11 - resto
        if int(digits[9 + i]) != expected:
            return False
    return True


def formatar_cpf(cpf: str) -> str:
    """Formata CPF para o padrão XXX.XXX.XXX-XX."""
    d = ''.join(c for c in cpf if c.isdigit())
    return f'{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:11]}'
