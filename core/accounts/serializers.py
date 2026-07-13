from rest_framework import serializers
from .models import Usuario, Role, Cidade
from .utils import validar_cpf, formatar_cpf


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'nome', 'descricao', 'ativo']


class CidadeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cidade
        fields = ['id', 'nome', 'uf', 'ativo']


class UsuarioSerializer(serializers.ModelSerializer):
    roles = RoleSerializer(many=True, read_only=True)
    cidade = CidadeSerializer(read_only=True)

    class Meta:
        model = Usuario
        fields = [
            'id', 'email', 'cpf', 'nome', 'sobrenome', 'perfil',
            'cidade', 'ativo', 'roles', 'cadastro_completo',
        ]
        read_only_fields = ['id', 'roles']


def _validar_cidade_e_hierarquia(data, *, instance=None, request=None):
    """
    Regras compartilhadas por criação/edição administrativa de usuário:
    - gestor/supervisor exigem cidade;
    - um gestor não pode criar/promover ninguém para gerente_geral, e só pode
      criar/promover gestor ou supervisor para a própria cidade (a cidade
      enviada é ignorada e substituída pela do próprio gestor).
    """
    perfil = data.get('perfil', instance.perfil if instance else None)

    if 'cidade' in data:
        cidade_efetiva = data['cidade']
    else:
        cidade_efetiva = instance.cidade if instance else None

    if perfil in Usuario.PERFIS_COM_CIDADE_OBRIGATORIA:
        if not cidade_efetiva:
            raise serializers.ValidationError(
                {'cidade': 'Cidade obrigatória para o perfil informado.'}
            )
    elif cidade_efetiva:
        raise serializers.ValidationError(
            {'cidade': 'Esse perfil não deve ter cidade própria.'}
        )

    ator = getattr(request, 'user', None) if request else None
    if ator is not None and getattr(ator, 'perfil', None) == 'gestor':
        if perfil == 'gerente_geral':
            raise serializers.ValidationError(
                {'perfil': 'Um gestor não pode criar ou promover usuários para gerente_geral.'}
            )
        if perfil in ('gestor', 'supervisor'):
            # Gestor só gerencia a própria cidade: força o vínculo, ignorando
            # qualquer cidade diferente que tenha sido enviada.
            data['cidade'] = ator.cidade

    return data


def _validate_cpf_field(value, *, instance=None):
    """Valida formato e dígitos verificadores do CPF e normaliza para XXX.XXX.XXX-XX."""
    if not validar_cpf(value):
        raise serializers.ValidationError('CPF inválido. Verifique os dígitos.')
    cpf_formatado = formatar_cpf(value)
    qs = Usuario.objects.filter(cpf=cpf_formatado)
    if instance is not None:
        qs = qs.exclude(pk=instance.pk)
    if qs.exists():
        raise serializers.ValidationError('Este CPF já está cadastrado.')
    return cpf_formatado


class UsuarioCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    cidade = serializers.PrimaryKeyRelatedField(
        queryset=Cidade.objects.all(), required=False, allow_null=True,
    )

    class Meta:
        model = Usuario
        fields = ['email', 'cpf', 'nome', 'perfil', 'cidade', 'password']

    def validate_cpf(self, value):
        if value:
            return _validate_cpf_field(value, instance=self.instance)
        return value

    def validate(self, data):
        return _validar_cidade_e_hierarquia(data, request=self.context.get('request'))

    def create(self, validated_data):
        password = validated_data.pop('password')
        usuario = Usuario(**validated_data)
        usuario.set_password(password)
        usuario.save()
        return usuario


class UsuarioSelfRegisterSerializer(UsuarioCreateSerializer):
    """
    Usado pelo cadastro público (/auth, sem autenticação).

    Sempre cria com perfil 'morador' — a criação de gestor/supervisor/
    gerente_geral só pode ser feita por um usuário já autorizado via /users.
    """
    class Meta(UsuarioCreateSerializer.Meta):
        fields = ['email', 'cpf', 'nome', 'password']

    def validate(self, data):
        # Cadastro público nunca passa por regras de cidade/hierarquia:
        # perfil é sempre 'morador', que não exige cidade própria.
        return data

    def create(self, validated_data):
        validated_data['perfil'] = 'morador'
        return super().create(validated_data)


class UsuarioUpdateSerializer(serializers.ModelSerializer):
    """Usado por /auth/me para que o titular atualize seus próprios dados."""
    class Meta:
        model = Usuario
        fields = ['nome', 'sobrenome', 'cpf']

    def validate_cpf(self, value):
        if value:
            return _validate_cpf_field(value, instance=self.instance)
        return value


class UsuarioManagerUpdateSerializer(serializers.ModelSerializer):
    """Usado por Gestores para atualizar dados de qualquer usuário."""
    cidade = serializers.PrimaryKeyRelatedField(
        queryset=Cidade.objects.all(), required=False, allow_null=True,
    )

    class Meta:
        model = Usuario
        fields = ['nome', 'sobrenome', 'cpf', 'perfil', 'cidade', 'ativo']

    def validate_cpf(self, value):
        if value:
            return _validate_cpf_field(value, instance=self.instance)
        return value

    def validate(self, data):
        return _validar_cidade_e_hierarquia(
            data, instance=self.instance, request=self.context.get('request'),
        )


class GoogleOAuthSerializer(serializers.Serializer):
    code = serializers.CharField()
    redirect_uri = serializers.CharField()


class GoogleCadastroComplementarSerializer(serializers.Serializer):
    """Formulário complementar obrigatório após o primeiro login via Google."""
    nome = serializers.CharField(max_length=150)
    sobrenome = serializers.CharField(max_length=100)
    cpf = serializers.CharField(max_length=14)

    def validate_nome(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Nome obrigatório.')
        return value

    def validate_sobrenome(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Sobrenome obrigatório.')
        return value

    def validate_cpf(self, value):
        request = self.context.get('request')
        instance = request.user if request else None
        return _validate_cpf_field(value, instance=instance)
