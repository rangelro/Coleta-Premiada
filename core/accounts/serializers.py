from rest_framework import serializers
from .models import Usuario, Role


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'nome', 'descricao', 'ativo']


class UsuarioSerializer(serializers.ModelSerializer):
    roles = RoleSerializer(many=True, read_only=True)

    class Meta:
        model = Usuario
        fields = [
            'id', 'email', 'cpf', 'nome', 'perfil', 'ativo', 'roles',
        ]
        read_only_fields = ['id', 'roles']


class UsuarioCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = Usuario
        fields = ['email', 'cpf', 'nome', 'perfil', 'password']

    def create(self, validated_data):
        password = validated_data.pop('password')
        usuario = Usuario(**validated_data)
        usuario.set_password(password)
        usuario.save()
        return usuario


class UsuarioUpdateSerializer(serializers.ModelSerializer):
    """Usado por /auth/me para que o titular atualize seus próprios dados."""
    class Meta:
        model = Usuario
        fields = ['nome', 'cpf']


class UsuarioManagerUpdateSerializer(serializers.ModelSerializer):
    """Usado por Gestores para atualizar dados de qualquer usuário."""
    class Meta:
        model = Usuario
        fields = ['nome', 'cpf', 'perfil', 'ativo']
