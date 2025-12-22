from rest_framework.views import APIView
from rest_framework import status
from decimal import Decimal
from datetime import datetime, timedelta
from django.db.models import Sum, Count
from django.db import transaction

from .models import Os
from contas_a_receber.models import Titulosreceber
from core.middleware import get_licenca_slug
from core.registry import get_licenca_db_config
from core.dominio_handler import tratar_sucesso, tratar_erro
from core.excecoes import ErroDominio


class GerarTitulosOS(APIView):
    def post(self, request, slug=None):
        try:
            banco = get_licenca_db_config(self.request)
            data = request.data
            os_os = data.get("os_os")
            os_clie = data.get("os_clie")
            os_tota = Decimal(data.get("os_tota", 0))
            entrada = Decimal(str(data.get("entrada", 0) or 0))
            forma_pagamento = data.get("forma_pagamento")
            parcelas = int(data.get("parcelas", 1))
            data_base = data.get("data_base", datetime.now().date().isoformat())
            
            if isinstance(data_base, str):
                data_base = datetime.strptime(data_base, "%Y-%m-%d").date()

            if not os_os or not os_clie or not os_tota:
                raise ErroDominio("os_os, os_clie e os_tota são obrigatórios.", codigo="dados_obrigatorios")

            if entrada < 0:
                raise ErroDominio("entrada não pode ser negativa.", codigo="entrada_negativa")
            if entrada > os_tota:
                raise ErroDominio("entrada não pode ser maior que o total.", codigo="entrada_excede_total")

            # Buscar a ordem de serviço para pegar empresa e filial
            try:
                ordem = Os.objects.using(banco).get(os_os=os_os)
                os_empr = ordem.os_empr
                os_fili = ordem.os_fili
            except Os.DoesNotExist:
                raise ErroDominio("Ordem de serviço não encontrada.", codigo="os_nao_encontrada", status_code=status.HTTP_404_NOT_FOUND)

            # Evita duplicidade: já existem títulos para esta OS/cliente
            ja_existe = Titulosreceber.objects.using(banco).filter(
                titu_empr=os_empr,
                titu_fili=os_fili,
                titu_seri="ORS",
                titu_titu=str(os_os),
                titu_clie=os_clie,
            ).exists()
            if ja_existe:
                raise ErroDominio(
                    "Já existe título com este pedido e cliente. Clique em Consultar.",
                    codigo="titulo_duplicado",
                    status_code=status.HTTP_409_CONFLICT
                )

            total_restante = (os_tota - entrada).quantize(Decimal("0.01"))
            valor_parcela = (total_restante / (parcelas if parcelas > 0 else 1)).quantize(Decimal("0.01"))
            diferenca = total_restante - (valor_parcela * (parcelas if parcelas > 0 else 1))

            titulos = []
            # Entrada como primeira parcela (se houver)
            offset = 1
            if entrada > 0:
                titulos.append(Titulosreceber(
                    titu_empr=os_empr,
                    titu_fili=os_fili,
                    titu_seri="ORS",
                    titu_titu=str(os_os),
                    titu_clie=os_clie,
                    titu_parc=1,
                    titu_valo=entrada,
                    titu_venc=data_base,
                    titu_form_reci=forma_pagamento or "",
                    titu_emis=datetime.now().date(),
                    titu_hist=f"Entrada da OS {os_os}",
                ))
                offset = 2

            # Demais parcelas
            for i in range(parcelas):
                vencimento = data_base + timedelta(days=30 * i)
                valor_atual = valor_parcela
                if i == 0:
                    valor_atual += diferenca

                titulos.append(Titulosreceber(
                    titu_empr=os_empr,
                    titu_fili=os_fili,
                    titu_seri="ORS",
                    titu_titu=str(os_os),
                    titu_clie=os_clie,
                    titu_parc=i + offset,
                    titu_valo=valor_atual,
                    titu_venc=vencimento,
                    titu_form_reci=forma_pagamento or "",
                    titu_emis=datetime.now().date(),
                    titu_hist=f"Título gerado da OS {os_os}",
                ))

            try:
                with transaction.atomic(using=banco):
                    Titulosreceber.objects.using(banco).bulk_create(titulos)
            except Exception:
                raise ErroDominio(
                    "Erro ao salvar títulos. Verifique se já existem.",
                    codigo="erro_salvar_titulos",
                    status_code=status.HTTP_409_CONFLICT
                )

            return tratar_sucesso({
                "detail": f"{len(titulos)} títulos gerados com sucesso.",
                "total_gerado": float(os_tota),
                "entrada": float(entrada),
                "total_parcelado": float(total_restante),
                "valor_parcelas": [float(t.titu_valo) for t in titulos],
                "vencimentos": [t.titu_venc.isoformat() for t in titulos]
            }, status_code=status.HTTP_201_CREATED)
            
        except Exception as e:
            return tratar_erro(e)


class RemoverTitulosOSView(APIView):
    def post(self, request, slug=None):
        try:
            banco = get_licenca_db_config(self.request)
            if not banco:
                raise ErroDominio("Banco não encontrado", codigo="banco_nao_encontrado")

            os_os = request.data.get("os_os")

            if not os_os:
                raise ErroDominio("os_os é obrigatório.", codigo="os_os_obrigatorio")

            try:
                ordem = Os.objects.using(banco).get(os_os=os_os)
            except Os.DoesNotExist:
                raise ErroDominio("Ordem de serviço não encontrada.", codigo="os_nao_encontrada", status_code=status.HTTP_404_NOT_FOUND)

            titulos = Titulosreceber.objects.using(banco).filter(
                titu_empr=ordem.os_empr,
                titu_fili=ordem.os_fili,
                titu_seri="ORS",
                titu_titu=str(os_os)
            )

            if not titulos.exists():
                raise ErroDominio("Nenhum título encontrado para essa OS.", codigo="titulos_nao_encontrados", status_code=status.HTTP_404_NOT_FOUND)

            count = titulos.count()
            titulos.delete()

            return tratar_sucesso(mensagem=f"{count} títulos removidos com sucesso.")
            
        except Exception as e:
            return tratar_erro(e)


class ConsultarTitulosOSView(APIView):
    def get(self, request, orde_nume, slug=None):
        try:
            banco = get_licenca_db_config(self.request)
            if not banco:
                raise ErroDominio("Banco não encontrado", codigo="banco_nao_encontrado")

            try:
                ordem = Os.objects.using(banco).get(
                    os_empr=request.query_params.get('empr'),
                    os_fili=request.query_params.get('fili'),
                    os_os=orde_nume
                )
            except Os.DoesNotExist:
                raise ErroDominio("Ordem de serviço não encontrada.", codigo="os_nao_encontrada", status_code=status.HTTP_404_NOT_FOUND)

            titulos = Titulosreceber.objects.using(banco).filter(
                titu_empr=ordem.os_empr,
                titu_fili=ordem.os_fili,
                titu_seri="ORS",
                titu_titu=str(ordem.os_os)
            ).order_by('titu_parc')

            if not titulos.exists():
                # Originalmente retornava 200 com mensagem. Vou manter mas estruturado.
                return tratar_sucesso({"titulos": [], "total": 0, "quantidade_parcelas": 0}, mensagem="Nenhum título encontrado para essa OS.")

            total = titulos.aggregate(
                total=Sum('titu_valo'),
                quantidade=Count('*')
            )

            dados_titulos = [{
                "parcela": titulo.titu_parc,
                "valor": float(titulo.titu_valo),
                "vencimento": titulo.titu_venc,
                "forma_pagamento": titulo.titu_form_reci,
                "status": titulo.titu_situ,
                "aberto": titulo.titu_aber,
                "empresa": titulo.titu_empr,
                "filial": titulo.titu_fili
            } for titulo in titulos]

            return tratar_sucesso({
                "titulos": dados_titulos,
                "total": float(total['total']),
                "quantidade_parcelas": total['quantidade']
            })
            
        except Exception as e:
            return tratar_erro(e)


class AtualizarTituloOSView(APIView):
    def post(self, request, slug=None):
        try:
            banco = get_licenca_db_config(self.request)
            if not banco:
                raise ErroDominio("Banco não encontrado", codigo="banco_nao_encontrado")

            data = request.data
            os_os = data.get("os_os")
            parcela = data.get("parcela")
            valor = data.get("valor")
            vencimento = data.get("vencimento")
            forma_pagamento = data.get("forma_pagamento")

            if not all([os_os, parcela, valor, vencimento]):
                raise ErroDominio("os_os, parcela, valor e vencimento são obrigatórios.", codigo="dados_obrigatorios")

            try:
                ordem = Os.objects.using(banco).get(os_os=os_os)
            except Os.DoesNotExist:
                raise ErroDominio("Ordem de serviço não encontrada.", codigo="os_nao_encontrada", status_code=status.HTTP_404_NOT_FOUND)

            try:
                titulo = Titulosreceber.objects.using(banco).get(
                    titu_empr=ordem.os_empr,
                    titu_fili=ordem.os_fili,
                    titu_seri="ORS",
                    titu_titu=str(os_os),
                    titu_parc=parcela
                )
            except Titulosreceber.DoesNotExist:
                raise ErroDominio("Título não encontrado.", codigo="titulo_nao_encontrado", status_code=status.HTTP_404_NOT_FOUND)

            if titulo.titu_aber and str(titulo.titu_aber).upper() != 'A':
                raise ErroDominio("Título não pode ser editado pois não está aberto.", codigo="titulo_nao_aberto", status_code=status.HTTP_409_CONFLICT)

            # Validação de limite: soma dos títulos não pode ultrapassar total da OS
            try:
                novo_valor = Decimal(str(valor))
            except Exception:
                raise ErroDominio("Valor inválido.", codigo="valor_invalido")
            if novo_valor < 0:
                raise ErroDominio("Valor da parcela não pode ser negativo.", codigo="valor_negativo")

            tota_limite = Decimal(str(getattr(ordem, 'os_tota', 0) or 0))
            soma_atual = Titulosreceber.objects.using(banco).filter(
                titu_empr=ordem.os_empr,
                titu_fili=ordem.os_fili,
                titu_seri="ORS",
                titu_titu=str(os_os)
            ).aggregate(total=Sum('titu_valo'))['total'] or Decimal('0')
            soma_sem_parcela = Decimal(str(soma_atual)) - Decimal(str(titulo.titu_valo or 0))
            if (soma_sem_parcela + novo_valor) > tota_limite:
                raise ErroDominio("Soma dos títulos excede o total da O.S.", codigo="limite_excedido", status_code=status.HTTP_409_CONFLICT)

            if isinstance(vencimento, str):
                vencimento = datetime.strptime(vencimento, "%Y-%m-%d").date()

            with transaction.atomic(using=banco):
                Titulosreceber.objects.using(banco).filter(
                    titu_empr=ordem.os_empr,
                    titu_fili=ordem.os_fili,
                    titu_seri="ORS",
                    titu_titu=str(os_os),
                    titu_parc=parcela
                ).update(
                    titu_valo=Decimal(str(valor)),
                    titu_venc=vencimento,
                    **({"titu_form_reci": forma_pagamento} if forma_pagamento is not None else {})
                )
                titulo = Titulosreceber.objects.using(banco).get(
                    titu_empr=ordem.os_empr,
                    titu_fili=ordem.os_fili,
                    titu_seri="ORS",
                    titu_titu=str(os_os),
                    titu_parc=parcela
                )

            return tratar_sucesso({
                "detail": "Título atualizado com sucesso.",
                "titulo": {
                    "parcela": titulo.titu_parc,
                    "valor": float(titulo.titu_valo),
                    "vencimento": titulo.titu_venc.isoformat(),
                    "forma_pagamento": titulo.titu_form_reci,
                    "status": titulo.titu_situ
                }
            })
            
        except Exception as e:
            return tratar_erro(e)
