import time
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model

from program.models import Programa, RegraPrograma, Imovel, SaldoPontos, ConstantePontuacao
from collection.models import RegistroColeta

Usuario = get_user_model()

class Command(BaseCommand):
    help = 'Preenche o banco de dados de forma idempotente para testes.'

    def handle(self, *args, **options):
        self.stdout.write("=== INICIANDO CRIAÇÃO DE DADOS DE TESTE ===")

        # 1. Constante
        constante, c = ConstantePontuacao.objects.get_or_create(
            pk=1, defaults={'points_por_kg': Decimal('1.5000')}
        )
        self.stdout.write(f"✓ Constante de pontuação: {'Criada' if c else 'Já existia'}")

        # 2. Programa
        hoje = timezone.now().date()
        programa, c = Programa.objects.get_or_create(
            nome='Ciclo 2026 - Coleta Verde',
            defaults={
                'descricao': 'Teste', 
                'ativo': True, 
                'data_inicio': hoje.replace(month=1, day=1), 
                'data_fim': hoje.replace(month=12, day=31), 
                'desconto_maximo': Decimal('40.00')
            }
        )
        self.stdout.write(f"✓ Programa {programa.nome}: {'Criado' if c else 'Já existia'}")

        # 3. Regras
        regra, c = RegraPrograma.objects.get_or_create(
            programa=programa,
            defaults={'pontos_por_real': Decimal('10.00'), 'minimo_para_beneficio': 50, 'permite_acumulo_ciclos': False}
        )

        # 4. Usuário Morador
        morador, c = Usuario.objects.get_or_create(
            email='joao.morador@exemplo.com',
            defaults={'nome': 'João da Silva', 'perfil': 'morador', 'ativo': True}
        )
        if c:
            morador.set_password('senha123')
            morador.save()
        self.stdout.write(f"✓ Morador {morador.email}: {'Criado' if c else 'Já existia'}")

        # 5. Imóvel
        imovel, c = Imovel.objects.get_or_create(
            inscricao='IPTU-123456',
            defaults={
                'titular': morador, 'cep': '59900-000', 'logradouro': 'Rua Teste', 
                'numero': '123', 'bairro': 'Centro', 'cidade': 'Natal', 'estado': 'RN', 
                'num_moradores': 3, 'ativo': True
            }
        )
        self.stdout.write(f"✓ Imóvel {imovel.inscricao}: {'Criado' if c else 'Já existia'}")

        # 6. Coleta e Saldo (Sempre cria nova para simular acúmulo)
        id_coleta = f'MANUAL-{int(time.time())}'
        RegistroColeta.objects.create(
            id_microservico=id_coleta, imovel=imovel, programa=programa, 
            peso_kg=Decimal('10.00'), pontuacao=Decimal('15.00'), data_hora_coleta=timezone.now()
        )
        self.stdout.write(f"✓ Nova coleta registrada: {id_coleta}")

        ciclo = hoje.strftime('%m-%Y')
        saldo, c = SaldoPontos.objects.get_or_create(
            imovel=imovel, programa=programa, ciclo=ciclo,
            defaults={'desconto_percentual': Decimal('1.50')}
        )
        if not c:
            saldo.desconto_percentual += Decimal('1.50')
            saldo.save()
            self.stdout.write(f"✓ Saldo acumulado! Atual: {saldo.desconto_percentual}%")
        else:
            self.stdout.write(f"✓ Saldo inicial criado: {saldo.desconto_percentual}%")

        self.stdout.write("=== CONCLUÍDO COM SUCESSO ===")