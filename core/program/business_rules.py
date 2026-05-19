"""
Regras de negócio do programa Coleta Premiada.

O Core recebe a pontuação já calculada pelo microserviço de coleta.
A única responsabilidade aqui é garantir que o teto máximo de
desconto no IPTU (40% por ciclo/ano) seja respeitado.
"""

from decimal import Decimal

# Teto máximo de desconto no IPTU por ciclo (ano)
DESCONTO_MAXIMO = Decimal('40.00')  # 40%


def aplicar_teto(desconto_atual, novo_desconto):
    """
    Limita o desconto total ao teto de 40%.

    Args:
        desconto_atual: Desconto já acumulado no ciclo (Decimal).
        novo_desconto: Desconto a ser adicionado (Decimal).

    Returns:
        Decimal com o desconto efetivamente aplicável (pode ser
        menor que novo_desconto se ultrapassar o teto).
    """
    desconto_atual = Decimal(str(desconto_atual))
    novo_desconto = Decimal(str(novo_desconto))

    total = desconto_atual + novo_desconto
    if total > DESCONTO_MAXIMO:
        return max(DESCONTO_MAXIMO - desconto_atual, Decimal('0'))
    return novo_desconto
