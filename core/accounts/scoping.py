"""
Escopo por cidade para gestor/supervisor.

Gestor e supervisor só enxergam dados da própria cidade; gerente_geral
(e qualquer perfil fora de PERFIS_ESCOPADOS_POR_CIDADE, como morador — que já
tem seu próprio filtro por titularidade) enxerga tudo, sem restrição de cidade.
"""
# Apenas gestor/supervisor são restritos à própria cidade; gerente_geral,
# por ser hierarquicamente superior, vê todas as cidades.
PERFIS_ESCOPADOS_POR_CIDADE = ('gestor', 'supervisor')


def escopar_por_cidade(queryset, user, campo_cidade):
    """
    Restringe `queryset` à cidade do usuário quando ele for gestor/supervisor.

    `campo_cidade` é o caminho (lookup) até o CharField `cidade` de Imovel,
    ex: 'cidade', 'imovel__cidade', 'coleta__imovel__cidade'.
    """
    if getattr(user, 'perfil', None) in PERFIS_ESCOPADOS_POR_CIDADE:
        if not getattr(user, 'cidade_id', None):
            return queryset.none()
        return queryset.filter(**{campo_cidade: user.cidade.nome})
    return queryset


def usuario_pode_ver_cidade(user, cidade_nome):
    """
    Versão para checagem em objeto único (get_object), simétrica a
    `escopar_por_cidade`: nega acesso se gestor/supervisor tentar acessar um
    objeto de cidade diferente da sua.
    """
    if getattr(user, 'perfil', None) in PERFIS_ESCOPADOS_POR_CIDADE:
        return bool(user.cidade_id) and user.cidade.nome == cidade_nome
    return True
