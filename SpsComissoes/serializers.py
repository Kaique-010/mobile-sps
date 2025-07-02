from rest_framework import serializers
from decimal import Decimal
from datetime import timedelta
from django.db import transaction, IntegrityError
import logging
import time
from .models import ComissaoSps
from contas_a_pagar.models import Titulospagar
from contas_a_receber.models import Titulosreceber

logger = logging.getLogger(__name__)

class ComissaoSpsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComissaoSps
        fields = '__all__'
    
    

    def get_percentual_categoria(self, codigo):
        return {
            '1': 5, '2': 5, '3': 20, '4': 20, '5': 5,
        }.get(codigo, 0)

    def calcular_campos(self, validated_data):
        valor_total = Decimal(str(validated_data.get('comi_valo_tota', 0)))
        impostos = Decimal(str(validated_data.get('comi_impo', 0)))
        categoria = validated_data.get('comi_cate')
        parcelas = validated_data.get('comi_parc', 1)
        perc = self.get_percentual_categoria(categoria)

        liquido = round((valor_total - impostos) * (Decimal('1') - Decimal('0.135')), 2)
        comissao_total = round(liquido * (Decimal(str(perc)) / Decimal('100')), 2)
        comissao_parcela = round(comissao_total / max(parcelas, 1), 2)

        validated_data['comi_perc'] = perc
        validated_data['comi_valo_liqu'] = liquido
        validated_data['comi_comi_tota'] = comissao_total
        validated_data['comi_comi_parc'] = comissao_parcela
        return validated_data

    def gerar_titulos(self, instancia, banco):
        try:
            data_base = instancia.comi_data_entr
            parcelas = instancia.comi_parc
            func = instancia.comi_func
            cliente = instancia.comi_clie
            comissao_id = str(instancia.comi_id)

            valor_parcela_receber = round(instancia.comi_valo_tota / max(parcelas, 1), 2)
            valor_parcela_pagar = instancia.comi_comi_parc

            titulos_receber_criados = []
            titulos_pagar_criados = []

            try:
                cliente_id = int(cliente) if cliente.isdigit() else 1
            except (ValueError, AttributeError):
                cliente_id = 1
                logger.warning(f"Cliente '{cliente}' inválido. Usando ID padrão 1")

            try:
                func_id = int(func) if func.isdigit() else 1
            except (ValueError, AttributeError):
                func_id = 1
                logger.warning(f"Funcionário '{func}' inválido. Usando ID padrão 1")

            categorias_prefixos = {
                '1': 'MEL',
                '2': 'IMP',
                '3': 'DAS',
                '4': 'MOB',
                '5': 'VEN',
            }

            prefixo_categoria = categorias_prefixos.get(instancia.comi_cate, 'UNK')
            comissao_id_str = str(instancia.comi_id).zfill(2)
            codigo_base = f"{prefixo_categoria}{comissao_id_str}"

            # TÍTULOS A RECEBER
            for i in range(parcelas):
                sufixo = str(i + 1).zfill(3)
                titulo_receber = f"{codigo_base}-{sufixo}"

                try:
                    titulo_obj = Titulosreceber.objects.using(banco).create(
                        titu_empr=instancia.comi_empr,
                        titu_fili=instancia.comi_fili,
                        titu_clie=cliente_id,
                        titu_titu=titulo_receber,
                        titu_parc=sufixo,
                        titu_seri=prefixo_categoria,
                        titu_valo=valor_parcela_receber,
                        titu_venc=data_base + timedelta(days=30 * i),
                        titu_emis=data_base,
                        titu_hist=f"Parcela {i+1}/{parcelas} - Recebimento por {instancia.comi_cate} - {cliente}",
                        titu_form_reci='54'
                    )
                    titulos_receber_criados.append(titulo_obj.titu_titu)
                except IntegrityError as e:
                    logger.error(f"Erro ao criar título a receber {titulo_receber}: {str(e)}")
                    raise Exception(f"Erro ao criar título a receber: título duplicado ou dados inválidos")

            # TÍTULOS A PAGAR
            for i in range(parcelas):
                sufixo = str(i + 1).zfill(3)
                titulo_pagar = f"{codigo_base}-{sufixo}"

                try:
                    titulo_obj = Titulospagar.objects.using(banco).create(
                        titu_empr=instancia.comi_empr,
                        titu_fili=instancia.comi_fili,
                        titu_forn=func_id,
                        titu_titu=titulo_pagar,
                        titu_parc=sufixo,
                        titu_seri=prefixo_categoria,
                        titu_valo=valor_parcela_pagar,
                        titu_venc=data_base + timedelta(days=30 * i),
                        titu_emis=data_base,
                        titu_hist=f"Parcela {i+1}/{parcelas} - Comissão {instancia.comi_cate} - {func}",
                        
                    )
                    titulos_pagar_criados.append(titulo_obj.titu_titu)
                except IntegrityError as e:
                    logger.error(f"Erro ao criar título a pagar {titulo_pagar}: {str(e)}")
                    raise Exception(f"Erro ao criar título a pagar: título duplicado ou dados inválidos")

            logger.info(f"Títulos criados para comissão {comissao_id}: {len(titulos_receber_criados)} a receber, {len(titulos_pagar_criados)} a pagar")

        except Exception as e:
            logger.error(f"Erro ao gerar títulos para comissão {instancia.comi_id}: {str(e)}")
            raise


    def create(self, validated_data):
        banco = self.context.get('banco', 'default')
        validated_data = self.calcular_campos(validated_data)
        
        try:
            with transaction.atomic(using=banco):
                # Criar instância manualmente devido ao managed=False
                instancia = ComissaoSps(**validated_data)
                instancia.save(using=banco)
                
                # Gerar títulos relacionados
                self.gerar_titulos(instancia, banco)
                
                logger.info(f"Comissão criada com sucesso: {instancia.comi_id}")
                return instancia
                
        except IntegrityError as e:
            error_msg = str(e).lower()
            logger.error(f"Erro de integridade ao criar comissão: {str(e)}")
            
            if 'unique' in error_msg or 'duplicate' in error_msg:
                raise serializers.ValidationError("Já existe uma comissão com estes dados. Verifique os campos empresa, filial e funcionário.")
            elif 'foreign key' in error_msg:
                raise serializers.ValidationError("Dados de referência inválidos. Verifique se empresa, filial, cliente e funcionário existem no sistema.")
            else:
                raise serializers.ValidationError("Erro de integridade no banco de dados. Verifique os dados informados.")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Erro inesperado ao criar comissão: {error_msg}")

            # Diagnóstico explícito no front com erro real:
            raise serializers.ValidationError(f"Erro inesperado: {error_msg}")

    def update(self, instance, validated_data):
        banco = self.context.get('banco', 'default')
        validated_data = self.calcular_campos(validated_data)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(using=banco)
        return instance

    
    