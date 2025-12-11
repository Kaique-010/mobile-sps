from rest_framework import viewsets, pagination
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from collections import defaultdict, Counter
from .models import HistoricoWorkflow
from .serializers_historico import HistoricoWorkflowSerializer
from core.registry import get_licenca_db_config


class PaginacaoResultados(pagination.PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


def segundos_para_hhmmss(segundos):
    horas = int(segundos // 3600)
    minutos = int((segundos % 3600) // 60)
    segundos_rest = int(segundos % 60)
    return f"{horas:02d}:{minutos:02d}:{segundos_rest:02d}"


class HistoricoWorkflowViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Endpoint para histórico de workflows.
    Calcula o tempo que cada OS ficou em cada setor.
    """
    serializer_class = HistoricoWorkflowSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['hist_empr', 'hist_fili', 'hist_orde']
    pagination_class = PaginacaoResultados

    def get_queryset(self):
        banco = get_licenca_db_config(self.request) or 'default'
        empresa_id = self.request.headers.get("X-Empresa") or self.request.query_params.get('hist_empr')
        filial_id = self.request.headers.get("X-Filial") or self.request.query_params.get('hist_fili')
        return HistoricoWorkflow.objects.using(banco).filter(
            hist_empr=empresa_id,
            hist_fili=filial_id
        ).order_by('hist_orde', 'hist_data')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        tempos_por_os = defaultdict(lambda: defaultdict(int))
        workflows = defaultdict(list)
        
        # DEBUG: vamos ver quantos eventos vieram
        total_eventos = queryset.count()
        print(f"Total de eventos encontrados: {total_eventos}")
        
        # Agrupa eventos por OS
        for h in queryset:
            workflows[h.hist_orde].append(h)
        
        for os, eventos in workflows.items():
            print(f"OS {os} tem {len(eventos)} eventos")
        
        # Processa cada OS
        from datetime import datetime, timezone
        
        for ordem, eventos in workflows.items():
            # Garante ordem cronológica
            eventos.sort(key=lambda x: x.hist_data)

            if not eventos:
                continue

            # Calcula tempo entre movimentações consecutivas
            for i in range(len(eventos) - 1):
                atual = eventos[i]
                proximo = eventos[i + 1]

                # O setor onde a OS está é o DESTINO da movimentação atual
                setor_atual = atual.hist_seto_dest
                
                # Ignora se não tem setor de destino definido
                if not setor_atual:
                    continue

                # Calcula quanto tempo ficou neste setor (até a próxima movimentação)
                delta = (proximo.hist_data - atual.hist_data).total_seconds()
                
                # Ignora intervalos negativos ou zero
                if delta <= 0:
                    continue

                # Acumula o tempo no setor
                tempos_por_os[ordem][f"Setor_{setor_atual}"] += delta
            
            # Se a OS tem apenas 1 evento ou o último evento tem setor destino,
            # calcula tempo até agora (para OSs em andamento)
            ultimo_evento = eventos[-1]
            if ultimo_evento.hist_seto_dest:
                # Calcula tempo desde o último evento até agora
                agora = datetime.now(timezone.utc)
                
                # Remove timezone do hist_data se necessário para comparação
                ultima_data = ultimo_evento.hist_data
                if ultima_data.tzinfo is None:
                    agora = datetime.now()
                
                delta_ate_agora = (agora - ultima_data).total_seconds()
                
                # Só adiciona se for positivo e menor que 30 dias (evita bugs)
                if 0 < delta_ate_agora < (30 * 24 * 3600):
                    setor_key = f"Setor_{ultimo_evento.hist_seto_dest}"
                    tempos_por_os[ordem][setor_key] += delta_ate_agora
        
        # --- DETALHE POR OS ---
        detalhe_os = []
        resumo_setor_total = Counter()
        
        for ordem, setores in tempos_por_os.items():
            if not setores:
                continue
                
            # Converte segundos para HH:MM:SS
            setores_dict = {s: segundos_para_hhmmss(sec) for s, sec in setores.items()}
            
            # Identifica setor com mais e menos tempo
            setor_mais = max(setores.items(), key=lambda x: x[1])
            setor_menos = min(setores.items(), key=lambda x: x[1])
            
            detalhe_os.append({
                "ordem": ordem,
                "tempos_por_setor": setores_dict,
                "setor_mais_tempo": {
                    "setor": setor_mais[0],
                    "segundos": setor_mais[1],
                    "hhmmss": segundos_para_hhmmss(setor_mais[1])
                },
                "setor_menos_tempo": {
                    "setor": setor_menos[0],
                    "segundos": setor_menos[1],
                    "hhmmss": segundos_para_hhmmss(setor_menos[1])
                },
            })
            
            # Acumula para o resumo geral
            for setor, segundos in setores.items():
                resumo_setor_total[setor] += segundos
        
        # --- RESUMO GERAL POR SETOR ---
        resumo_setor = [
            {
                "setor": setor,
                "total_segundos": total,
                "total_hhmmss": segundos_para_hhmmss(total)
            }
            for setor, total in resumo_setor_total.items()
        ]
        resumo_setor = sorted(resumo_setor, key=lambda x: x["total_segundos"], reverse=True)
        
        # --- PAGINAÇÃO ---
        page = self.paginate_queryset(detalhe_os)
        if page is not None:
            return self.get_paginated_response({
                "detalhe_por_os": page,
                "resumo_setor_total": resumo_setor
            })
        
        empresa_id = self.request.headers.get("X-Empresa") or self.request.query_params.get('hist_empr')
        filial_id = self.request.headers.get("X-Filial") or self.request.query_params.get('hist_fili')
        
        return Response({
            "empresa": empresa_id,
            "filial": filial_id,
            "detalhe_por_os": detalhe_os,
            "resumo_setor_total": resumo_setor
        })

        
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['banco'] = get_licenca_db_config(self.request)
        return context