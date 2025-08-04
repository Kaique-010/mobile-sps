from typing import List, Dict, Any
from datetime import datetime
import re

class ConversationMemory:
    def __init__(self, max_history: int = 15):
        self.history: List[Dict] = []
        self.context: Dict[str, Any] = {
            'empresa_atual': None,
            'filial_atual': None,
            'periodo_atual': None,
            'ultimo_resultado': None,
            'topico_atual': None,
            'filtros_ativos': {},
            'padroes_consulta': []
        }
        self.max_history = max_history
    
    def add_interaction(self, pergunta: str, resposta: str, sql: str = None, resultado: Any = None):
        """Adiciona interação ao histórico com análise inteligente"""
        interaction = {
            'timestamp': datetime.now(),
            'pergunta': pergunta,
            'resposta': resposta,
            'sql': sql,
            'resultado': resultado,
            'contexto_extraido': self._extract_context(pergunta, resultado)
        }
        
        self.history.append(interaction)
        
        # Manter apenas as últimas N interações
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        
        # Atualizar contexto
        self._update_context(pergunta, resultado, sql)
        
        # Aprender padrões
        self._learn_patterns(pergunta, sql)
    
    def _extract_context(self, pergunta: str, resultado: Any) -> Dict:
        """Extrai contexto específico da pergunta e resultado"""
        context = {}
        pergunta_lower = pergunta.lower()
        
        # Detectar entidades mencionadas
        if 'cliente' in pergunta_lower:
            context['entidade'] = 'cliente'
        elif 'produto' in pergunta_lower:
            context['entidade'] = 'produto'
        elif 'pedido' in pergunta_lower or 'venda' in pergunta_lower:
            context['entidade'] = 'pedido'
        elif 'vendedor' in pergunta_lower or 'funcionario' in pergunta_lower:
            context['entidade'] = 'vendedor'
        
        # Detectar períodos
        if re.search(r'\d{4}', pergunta):
            anos = re.findall(r'\d{4}', pergunta)
            context['ano'] = anos[-1]  # Último ano mencionado
        
        if any(mes in pergunta_lower for mes in ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho']):
            context['periodo_especifico'] = True
        
        # Detectar tipo de análise
        if any(palavra in pergunta_lower for palavra in ['total', 'soma', 'quanto']):
            context['tipo_analise'] = 'agregacao'
        elif any(palavra in pergunta_lower for palavra in ['lista', 'mostre', 'quais']):
            context['tipo_analise'] = 'listagem'
        elif any(palavra in pergunta_lower for palavra in ['grafico', 'chart', 'visualiza']):
            context['tipo_analise'] = 'grafico'
        
        return context
    
    def _update_context(self, pergunta: str, resultado: Any, sql: str = None):
        """Atualiza contexto baseado na pergunta e resultado"""
        pergunta_lower = pergunta.lower()
        
        # Detectar tópicos com mais precisão
        if any(word in pergunta_lower for word in ['cliente', 'clientes']):
            self.context['topico_atual'] = 'clientes'
        elif any(word in pergunta_lower for word in ['vendedor', 'vendedores', 'funcionario']):
            self.context['topico_atual'] = 'vendedores'
        elif any(word in pergunta_lower for word in ['produto', 'produtos', 'estoque']):
            self.context['topico_atual'] = 'produtos'
        elif any(word in pergunta_lower for word in ['pedido', 'pedidos', 'venda']):
            self.context['topico_atual'] = 'pedidos'
        
        # Extrair filtros ativos do SQL
        if sql:
            self._extract_filters_from_sql(sql)
        
        # Detectar empresa/filial do resultado
        if resultado and isinstance(resultado, list) and len(resultado) > 0:
            first_result = resultado[0]
            if isinstance(first_result, dict):
                for key, value in first_result.items():
                    if 'empr' in key.lower():
                        self.context['empresa_atual'] = value
                    elif 'fili' in key.lower():
                        self.context['filial_atual'] = value
        
        self.context['ultimo_resultado'] = resultado
    
    def _extract_filters_from_sql(self, sql: str):
        """Extrai filtros ativos do SQL"""
        sql_lower = sql.lower()
        
        # Detectar filtros de data
        if 'where' in sql_lower and any(op in sql_lower for op in ['>=', '<=', 'between']):
            if any(campo in sql_lower for campo in ['data', 'date']):
                self.context['filtros_ativos']['data'] = True
        
        # Detectar filtros de empresa
        if 'empr' in sql_lower:
            self.context['filtros_ativos']['empresa'] = True
    
    def _learn_patterns(self, pergunta: str, sql: str):
        """Aprende padrões de consulta para sugestões futuras"""
        if not sql:
            return
        
        pattern = {
            'pergunta_tipo': self._classify_question(pergunta),
            'sql_pattern': self._extract_sql_pattern(sql),
            'timestamp': datetime.now()
        }
        
        self.context['padroes_consulta'].append(pattern)
        
        # Manter apenas os últimos 20 padrões
        if len(self.context['padroes_consulta']) > 20:
            self.context['padroes_consulta'] = self.context['padroes_consulta'][-20:]
    
    def _classify_question(self, pergunta: str) -> str:
        """Classifica o tipo de pergunta"""
        pergunta_lower = pergunta.lower()
        
        if any(palavra in pergunta_lower for palavra in ['quantos', 'quantidade', 'total']):
            return 'contagem'
        elif any(palavra in pergunta_lower for palavra in ['valor', 'preco', 'custo']):
            return 'monetario'
        elif any(palavra in pergunta_lower for palavra in ['lista', 'mostre', 'quais']):
            return 'listagem'
        elif any(palavra in pergunta_lower for palavra in ['melhor', 'maior', 'menor']):
            return 'ranking'
        else:
            return 'geral'
    
    def _extract_sql_pattern(self, sql: str) -> str:
        """Extrai padrão do SQL para reutilização"""
        sql_lower = sql.lower()
        
        if 'group by' in sql_lower:
            return 'agregacao'
        elif 'order by' in sql_lower:
            return 'ordenacao'
        elif 'join' in sql_lower:
            return 'relacionamento'
        else:
            return 'simples'
    
    def get_context_prompt(self) -> str:
        """Gera prompt com contexto inteligente para o agente"""
        context_parts = []
        
        if self.context['topico_atual']:
            context_parts.append(f"Tópico atual: {self.context['topico_atual']}")
        
        if self.context['empresa_atual']:
            context_parts.append(f"Empresa em foco: {self.context['empresa_atual']}")
        
        if self.context['filtros_ativos']:
            filtros = ', '.join(self.context['filtros_ativos'].keys())
            context_parts.append(f"Filtros ativos: {filtros}")
        
        # Adicionar contexto das últimas 3 interações
        if len(self.history) > 0:
            context_parts.append("\nÚltimas consultas:")
            for i, interaction in enumerate(self.history[-3:], 1):
                context_parts.append(f"{i}. {interaction['pergunta'][:80]}...")
        
        if context_parts:
            return "\n\nCONTEXTO DA CONVERSA:\n" + "\n".join(f"- {part}" for part in context_parts)
        
        return ""
    
    def get_suggestions(self) -> List[str]:
        """Gera sugestões inteligentes baseadas no contexto e padrões"""
        suggestions = []
        
        # Sugestões baseadas no tópico atual
        if self.context['topico_atual'] == 'clientes':
            suggestions.extend([
                "Qual o valor total de vendas para esses clientes?",
                "Mostre um gráfico dos pedidos por cliente",
                "Quais vendedores atendem esses clientes?",
                "Qual a frequência de compras desses clientes?"
            ])
        elif self.context['topico_atual'] == 'produtos':
            suggestions.extend([
                "Qual o estoque atual desses produtos?",
                "Gere um gráfico de vendas por produto",
                "Qual a margem de lucro desses produtos?",
                "Mostre a sazonalidade de vendas"
            ])
        elif self.context['topico_atual'] == 'pedidos':
            suggestions.extend([
                "Quais produtos foram mais vendidos?",
                "Crie um gráfico de faturamento por período",
                "Qual vendedor teve melhor performance?",
                "Mostre a evolução das vendas"
            ])
        else:
            # Sugestões gerais baseadas na última consulta
            if len(self.history) > 0:
                ultima_pergunta = self.history[-1]['pergunta'].lower()
                if 'quantidade' in ultima_pergunta or 'total' in ultima_pergunta:
                    suggestions.extend([
                        "Gere um gráfico desses dados",
                        "Compare com o período anterior",
                        "Mostre a distribuição por categoria",
                        "Analise a tendência temporal"
                    ])
        
        # Sugestões baseadas em padrões aprendidos
        recent_patterns = self.context['padroes_consulta'][-3:]
        for pattern in recent_patterns:
            if pattern['pergunta_tipo'] == 'contagem':
                suggestions.append("Visualizar esses dados em gráfico")
            elif pattern['pergunta_tipo'] == 'monetario':
                suggestions.append("Analisar rentabilidade e margens")
        
        # Sempre incluir sugestões de visualização se não houver
        if not any('gráfico' in s.lower() for s in suggestions):
            suggestions.append("Gere um gráfico com esses dados")
        
        # Remover duplicatas e limitar
        suggestions = list(dict.fromkeys(suggestions))  # Remove duplicatas mantendo ordem
        return suggestions[:4]  # Máximo 4 sugestões
    
    def get_smart_context_for_sql(self) -> str:
        """Retorna contexto específico para geração de SQL"""
        context_sql = []
        
        if self.context['empresa_atual']:
            context_sql.append(f"Focar na empresa {self.context['empresa_atual']}")
        
        if self.context['filtros_ativos']:
            context_sql.append("Manter filtros similares às consultas anteriores")
        
        # Analisar padrões recentes
        recent_sqls = [h.get('sql', '') for h in self.history[-3:] if h.get('sql')]
        if recent_sqls:
            if all('GROUP BY' in sql for sql in recent_sqls):
                context_sql.append("Usuário prefere consultas agregadas")
            if all('ORDER BY' in sql for sql in recent_sqls):
                context_sql.append("Sempre ordenar resultados")
        
        return " | ".join(context_sql) if context_sql else ""

# Instância global da memória
conversation_memory = ConversationMemory()