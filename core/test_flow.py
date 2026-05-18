"""
Script de teste do fluxo completo:
  1. Cria um Usuário + Imóvel (se não existirem)
  2. Publica uma pesagem na fila.pesagens usando o ID do imóvel
  3. Aguarda o consumer processar
  4. Confirma que RegistroColeta e SaldoPontos foram criados
"""
import os
import sys
import time
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from accounts.models import Usuario
from program.models import Imovel, SaldoPontos
from collection.models import RegistroColeta
from messaging.producer import publish_message


def run_test():
    print("=== Teste de fluxo: Pesagem via RabbitMQ ===\n")

    # 1. Usuário morador
    usuario, criado = Usuario.objects.get_or_create(
        email="morador.teste@coletapremiada.com.br",
        defaults={
            'nome': 'Morador Teste',
            'perfil': 'morador',
        }
    )
    if criado:
        usuario.set_password("senha_teste_123")
        usuario.save()
        print(f"  [+] Usuário criado: {usuario.email}")
    else:
        print(f"  [=] Usuário já existe: {usuario.email}")

    # 2. Imóvel
    imovel, criado = Imovel.objects.get_or_create(
        inscricao="TEST-999",
        defaults={
            'titular': usuario,
            'cep': '59900-000',
            'logradouro': 'Rua das Flores',
            'numero': '100',
            'bairro': 'Centro',
            'cidade': 'Pau dos Ferros',
            'estado': 'RN',
            'num_moradores': 2,
            'ativo': True,
        }
    )
    if criado:
        print(f"  [+] Imóvel criado: ID={imovel.id} | Inscrição={imovel.inscricao}")
    else:
        print(f"  [=] Imóvel já existe: ID={imovel.id} | Inscrição={imovel.inscricao}")

    # 3. ID único para essa pesagem de teste (evita duplicatas)
    id_pesagem = f"test_flow_{int(time.time())}"

    payload = {
        "id": id_pesagem,
        "imovel_id": imovel.id,         # <-- chave primária do banco
        "pontuacao": 18.0,
        "data_hora": timezone.now().isoformat(),
        "material": "Plástico",
        "peso_kg": 2.5,
    }

    print(f"\n  [→] Publicando pesagem na fila: id={id_pesagem}, imovel_id={imovel.id}")
    try:
        publish_message('fila.pesagens', payload)
        print("  [✓] Mensagem publicada com sucesso!")
    except Exception as e:
        print(f"  [✗] Erro ao publicar: {e}")
        sys.exit(1)

    # 4. Aguarda o consumer processar
    print("\n  [⏳] Aguardando 4 segundos para o consumer processar...")
    time.sleep(4)

    # 5. Valida no banco
    print("\n  [?] Verificando banco de dados...")
    coleta = RegistroColeta.objects.filter(id_microservico=id_pesagem).first()
    if coleta:
        print(f"  [✓] SUCESSO — RegistroColeta criado! ID={coleta.id}, "
              f"Material={coleta.material}, Pontos={coleta.pontuacao}")
    else:
        print("  [✗] FALHA — RegistroColeta NÃO encontrado no banco.")

    saldo = SaldoPontos.objects.filter(imovel=imovel).order_by('-atualizado').first()
    if saldo:
        print(f"  [✓] SUCESSO — SaldoPontos atualizado! "
              f"Ciclo={saldo.ciclo}, Desconto={saldo.desconto_percentual}%")
    else:
        print("  [✗] FALHA — SaldoPontos NÃO encontrado.")

    print("\n=== Fim do teste ===")


if __name__ == '__main__':
    run_test()
