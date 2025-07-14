#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para popular automaticamente as tabelas de parâmetros do sistema
Baseado nos parâmetros definidos nos arquivos utils_*.py
"""

import os
import sys
import django
from django.db import transaction
from django.core.management.base import BaseCommand

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from parametros_admin.models import Modulo, ParametroSistema


class PopulateParametros:
    """
    Classe para popular parâmetros do sistema automaticamente
    """
    
    def __init__(self):
        self.modulos_parametros = {
            'Entradas_Estoque': {
                'nome': 'Entradas_Estoque',
                'descricao': 'Módulo de controle de estoque',
                'icone': 'fas fa-boxes',
                'ordem': 1,
                'parametros': [
                    {
                        'nome': 'entrada_automatica_estoque',
                        'descricao': 'Permite entrada automática de estoque',
                        'valor_padrao': True,
                        'ativo': True
                    },
                    {
                        'nome': 'saida_automatica_estoque',
                        'descricao': 'Permite saída automática de estoque',
                        'valor_padrao': True,
                        'ativo': True
                    },
                    {
                        'nome': 'pedido_volta_estoque',
                        'descricao': 'Permite volta de estoque ao cancelar pedido',
                        'valor_padrao': True,
                        'ativo': True
                    },
                    {
                        'nome': 'alerta_estoque_minimo',
                        'descricao': 'Exibe alertas quando estoque atingir o mínimo',
                        'valor_padrao': True,
                        'ativo': True
                    },
                    {
                        'nome': 'permitir_estoque_negativo',
                        'descricao': 'Permite estoque negativo',
                        'valor_padrao': False,
                        'ativo': True
                    },
                    {
                        'nome': 'calculo_automatico_custo',
                        'descricao': 'Calcula custo automaticamente nas entradas',
                        'valor_padrao': True,
                        'ativo': True
                    }
                ]
            },
            'Pedidos': {
                'nome': 'Pedidos',
                'descricao': 'Módulo de pedidos de venda',
                'icone': 'fas fa-shopping-cart',
                'ordem': 2,
                'parametros': [
                    {
                        'nome': 'usar_preco_prazo',
                        'descricao': 'Usar preço a prazo nos pedidos',
                        'valor_padrao': False,
                        'ativo': True
                    },
                    {
                        'nome': 'usar_ultimo_preco',
                        'descricao': 'Usar último preço aplicado',
                        'valor_padrao': False,
                        'ativo': True
                    },
                    {
                        'nome': 'desconto_pedido',
                        'descricao': 'Permite desconto em pedidos',
                        'valor_padrao': True,
                        'ativo': True
                    },
                    {
                        'nome': 'pedido_volta_estoque',
                        'descricao': 'Volta estoque ao cancelar pedido',
                        'valor_padrao': True,
                        'ativo': True
                    },
                    {
                        'nome': 'validar_estoque_pedido',
                        'descricao': 'Validar estoque ao criar pedido',
                        'valor_padrao': True,
                        'ativo': True
                    },
                    {
                        'nome': 'calcular_frete_automatico',
                        'descricao': 'Calcular frete automaticamente',
                        'valor_padrao': False,
                        'ativo': True
                    }
                ]
            },
            'Orcamentos': {
                'nome': 'Orcamentos',
                'descricao': 'Módulo de orçamentos',
                'icone': 'fas fa-file-invoice-dollar',
                'ordem': 3,
                'parametros': [
                    {
                        'nome': 'baixa_estoque_orcamento',
                        'descricao': 'Baixar estoque ao criar orçamento',
                        'valor_padrao': False,
                        'ativo': True
                    },
                    {
                        'nome': 'usar_preco_prazo',
                        'descricao': 'Usar preço a prazo nos orçamentos',
                        'valor_padrao': False,
                        'ativo': True
                    },
                    {
                        'nome': 'usar_ultimo_preco',
                        'descricao': 'Usar último preço aplicado',
                        'valor_padrao': False,
                        'ativo': True
                    },
                    {
                        'nome': 'desconto_orcamento',
                        'descricao': 'Permite desconto em orçamentos',
                        'valor_padrao': True,
                        'ativo': True
                    },
                    {
                        'nome': 'validade_orcamento_dias',
                        'descricao': 'Dias de validade do orçamento (valor numérico)',
                        'valor_padrao': True,  # Representa 30 dias como padrão
                        'ativo': True
                    },
                    {
                        'nome': 'conversao_automatica_pedido',
                        'descricao': 'Conversão automática de orçamento para pedido',
                        'valor_padrao': False,
                        'ativo': True
                    }
                ]
            },
            'Produtos': {
                'nome': 'Produtos',
                'descricao': 'Módulo de produtos e preços',
                'icone': 'fas fa-box',
                'ordem': 4,
                'parametros': [
                    {
                        'nome': 'controle_preco_automatico',
                        'descricao': 'Controle automático de preços',
                        'valor_padrao': False,
                        'ativo': True
                    },
                    {
                        'nome': 'margem_lucro_automatica',
                        'descricao': 'Cálculo automático de margem de lucro',
                        'valor_padrao': False,
                        'ativo': True
                    },
                    {
                        'nome': 'sincronizar_precos_filiais',
                        'descricao': 'Sincronizar preços entre filiais',
                        'valor_padrao': False,
                        'ativo': True
                    }
                ]
            },
            'Financeiro': {
                'nome': 'Financeiro',
                'descricao': 'Módulo financeiro',
                'icone': 'fas fa-dollar-sign',
                'ordem': 5,
                'parametros': [
                    {
                        'nome': 'gerar_contas_automatico',
                        'descricao': 'Gerar contas a receber automaticamente',
                        'valor_padrao': True,
                        'ativo': True
                    },
                    {
                        'nome': 'calcular_juros_automatico',
                        'descricao': 'Calcular juros automaticamente',
                        'valor_padrao': False,
                        'ativo': True
                    },
                    {
                        'nome': 'permitir_desconto_financeiro',
                        'descricao': 'Permite desconto financeiro',
                        'valor_padrao': True,
                        'ativo': True
                    }
                ]
            }
        }
    
    def criar_modulos(self):
        """
        Cria os módulos no banco de dados
        """
        print("Criando módulos...")
        
        for modulo_key, modulo_data in self.modulos_parametros.items():
            modulo, created = Modulo.objects.get_or_create(
                modu_nome=modulo_data['nome'],
                defaults={
                    'modu_desc': modulo_data['descricao'],
                    'modu_ativ': True,
                    'modu_icon': modulo_data['icone'],
                    'modu_orde': modulo_data['ordem']
                }
            )
            
            if created:
                print(f"  ✓ Módulo '{modulo_data['nome']}' criado")
            else:
                print(f"  - Módulo '{modulo_data['nome']}' já existe")
    
    def criar_parametros_empresa_filial(self, empresa_id, filial_id):
        """
        Cria parâmetros para uma empresa/filial específica
        """
        print(f"Criando parâmetros para Empresa {empresa_id}, Filial {filial_id}...")
        
        for modulo_key, modulo_data in self.modulos_parametros.items():
            try:
                modulo = Modulo.objects.get(modu_nome=modulo_data['nome'])
                
                for param_data in modulo_data['parametros']:
                    parametro, created = ParametroSistema.objects.get_or_create(
                        para_empr=empresa_id,
                        para_fili=filial_id,
                        para_modu=modulo,
                        para_nome=param_data['nome'],
                        defaults={
                            'para_desc': param_data['descricao'],
                            'para_valo': param_data['valor_padrao'],
                            'para_ativ': param_data['ativo'],
                            'para_usua_alte': 1  # Usuário admin
                        }
                    )
                    
                    if created:
                        print(f"    ✓ Parâmetro '{param_data['nome']}' criado para {modulo_data['nome']}")
                    else:
                        print(f"    - Parâmetro '{param_data['nome']}' já existe para {modulo_data['nome']}")
                        
            except Modulo.DoesNotExist:
                print(f"    ✗ Módulo '{modulo_data['nome']}' não encontrado")
    
    def popular_todas_empresas_filiais(self):
        """
        Popula parâmetros para todas as combinações empresa/filial
        Você pode modificar esta função para buscar as empresas/filiais do seu banco
        """

        empresas = [1, 2, 3]
        filiais = [1, 2]
        
        for empresa_id in empresas:
            for filial_id in filiais:
                self.criar_parametros_empresa_filial(empresa_id, filial_id)
    
    def popular_empresa_filial_especifica(self, empresa_id, filial_id):
        """
        Popula parâmetros para uma empresa/filial específica
        """
        self.criar_parametros_empresa_filial(empresa_id, filial_id)
    
    def executar_populacao_completa(self):
        """
        Executa a população completa do sistema
        """
        print("=" * 60)
        print("INICIANDO POPULAÇÃO DE PARÂMETROS DO SISTEMA")
        print("=" * 60)
        
        try:
            with transaction.atomic():
                # Criar módulos
                self.criar_modulos()
                print()
                
                # Popular parâmetros para todas as empresas/filiais
                self.popular_todas_empresas_filiais()
                
                print()
                print("=" * 60)
                print("POPULAÇÃO CONCLUÍDA COM SUCESSO!")
                print("=" * 60)
                
        except Exception as e:
            print(f"\n✗ ERRO durante a população: {e}")
            print("Transação foi revertida.")
            raise
    
    def listar_parametros_existentes(self):
        """
        Lista todos os parâmetros existentes no sistema
        """
        print("=" * 60)
        print("PARÂMETROS EXISTENTES NO SISTEMA")
        print("=" * 60)
        
        modulos = Modulo.objects.all().order_by('modu_orde', 'modu_nome')
        
        for modulo in modulos:
            print(f"\nMódulo: {modulo.modu_nome} (ID: {modulo.modu_codi})")
            print(f"Descrição: {modulo.modu_desc}")
            print(f"Ativo: {'Sim' if modulo.modu_ativ else 'Não'}")
            
            parametros = ParametroSistema.objects.filter(para_modu=modulo).order_by('para_empr', 'para_fili', 'para_nome')
            
            if parametros.exists():
                print("Parâmetros:")
                for param in parametros:
                    status = "Ativo" if param.para_ativ else "Inativo"
                    valor = "Sim" if param.para_valo else "Não"
                    print(f"  - {param.para_nome} (Emp: {param.para_empr}, Fil: {param.para_fili}) = {valor} [{status}]")
            else:
                print("  Nenhum parâmetro configurado")


def main():
    """
    Função principal do script
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Popular parâmetros do sistema')
    parser.add_argument('--acao', choices=['popular', 'listar', 'empresa'], 
                       default='popular', help='Ação a executar')
    parser.add_argument('--empresa', type=int, help='ID da empresa (para ação empresa)')
    parser.add_argument('--filial', type=int, help='ID da filial (para ação empresa)')
    
    args = parser.parse_args()
    
    populate = PopulateParametros()
    
    if args.acao == 'popular':
        populate.executar_populacao_completa()
    elif args.acao == 'listar':
        populate.listar_parametros_existentes()
    elif args.acao == 'empresa':
        if not args.empresa or not args.filial:
            print("Para ação 'empresa', é necessário informar --empresa e --filial")
            return
        
        populate.criar_modulos()
        populate.popular_empresa_filial_especifica(args.empresa, args.filial)


if __name__ == '__main__':
    main()