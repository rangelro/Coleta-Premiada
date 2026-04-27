"""
Regras de negócio do programa Coleta Premiada.

Taxas de desconto no IPTU por kg de material reciclável entregue.
Base: média nacional de ~380 kg/ano por habitante adulto.
Meta: 1 morador → até 40% de desconto no IPTU por ciclo (ano).

Ajuste por moradores: residências com mais de 1 morador precisam
entregar 0,5 kg a mais por pessoa para cada kg da tabela base.
Isso é modelado como fator de diluição sobre o peso entregue.
"""

from decimal import Decimal

# ── Taxas de desconto (pontos percentuais por kg) ──────────────────
TAXA_DESCONTO = {
    'papel':     Decimal('0.10'),   # Papel / Papelão
    'plastico':  Decimal('0.05'),   # Plástico
    'aluminio':  Decimal('0.05'),   # Alumínio
    'vidro':     Decimal('0.03'),   # Vidro
    'metal':     Decimal('0.03'),   # Metal
    'eletronico': Decimal('0'),     # Eletrônico (sem desconto definido)
}

# ── Teto máximo de desconto no IPTU por ciclo ──────────────────────
DESCONTO_MAXIMO = Decimal('40.00')  # 40%


def calcular_desconto(peso_kg, material, num_moradores=1):
    """
    Calcula os pontos percentuais de desconto no IPTU gerados por
    uma entrega de material reciclável.

    Args:
        peso_kg: Peso em kg do material entregue (Decimal ou str).
        material: Tipo do material (chave de TAXA_DESCONTO).
        num_moradores: Quantidade de moradores na residência.

    Returns:
        Decimal com os pontos percentuais de desconto gerados.
    """
    peso = Decimal(str(peso_kg))
    taxa = TAXA_DESCONTO.get(material, Decimal('0'))

    # Fator de diluição por número de moradores
    if num_moradores > 1:
        fator = Decimal('1') + Decimal('0.5') * Decimal(num_moradores - 1)
        peso_efetivo = peso / fator
    else:
        peso_efetivo = peso

    return (peso_efetivo * taxa).quantize(Decimal('0.01'))


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
