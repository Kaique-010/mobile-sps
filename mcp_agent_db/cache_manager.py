import hashlib
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import pickle

class QueryCache:
    def __init__(self, ttl_minutes: int = 30, max_size: int = 100):
        self.cache: Dict[str, Dict] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
        self.max_size = max_size
        self.access_count = {}  # Para LRU
    
    def _generate_key(self, pergunta: str, slug: str) -> str:
        """Gera chave única para a consulta"""
        # Normalizar pergunta para melhor cache hit
        pergunta_normalizada = pergunta.lower().strip()
        pergunta_normalizada = ' '.join(pergunta_normalizada.split())  # Remove espaços extras
        content = f"{pergunta_normalizada}_{slug}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, pergunta: str, slug: str) -> Optional[Dict]:
        """Recupera resultado do cache se válido"""
        key = self._generate_key(pergunta, slug)
        
        if key in self.cache:
            cached_item = self.cache[key]
            if datetime.now() - cached_item['timestamp'] < self.ttl:
                # Atualizar contador de acesso para LRU
                self.access_count[key] = self.access_count.get(key, 0) + 1
                print(f"🎯 Cache hit: {pergunta[:50]}... (acessos: {self.access_count[key]})")
                return cached_item['result']
            else:
                # Remove item expirado
                self._remove_key(key)
        
        return None
    
    def set(self, pergunta: str, slug: str, resultado: Any, sql: str = None):
        """Armazena resultado no cache com LRU"""
        key = self._generate_key(pergunta, slug)
        
        # Se cache está cheio, remove o menos usado
        if len(self.cache) >= self.max_size:
            self._evict_lru()
        
        self.cache[key] = {
            'result': resultado,
            'sql': sql,
            'timestamp': datetime.now(),
            'pergunta_original': pergunta,
            'slug': slug
        }
        self.access_count[key] = 1
        print(f"💾 Cache stored: {pergunta[:50]}... (total: {len(self.cache)})")
    
    def _remove_key(self, key: str):
        """Remove chave do cache e contadores"""
        if key in self.cache:
            del self.cache[key]
        if key in self.access_count:
            del self.access_count[key]
    
    def _evict_lru(self):
        """Remove o item menos usado (LRU)"""
        if not self.cache:
            return
        
        # Encontrar chave com menor contador de acesso
        lru_key = min(self.access_count.keys(), key=lambda k: self.access_count[k])
        self._remove_key(lru_key)
        print(f"🗑️ Cache LRU eviction: {lru_key}")
    
    def clear_expired(self):
        """Remove itens expirados do cache"""
        now = datetime.now()
        expired_keys = [
            key for key, item in self.cache.items()
            if now - item['timestamp'] > self.ttl
        ]
        for key in expired_keys:
            self._remove_key(key)
        
        if expired_keys:
            print(f"🧹 Removed {len(expired_keys)} expired cache items")
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas do cache"""
        return {
            'total_items': len(self.cache),
            'max_size': self.max_size,
            'ttl_minutes': self.ttl.total_seconds() / 60,
            'most_accessed': max(self.access_count.items(), key=lambda x: x[1]) if self.access_count else None
        }

# Instância global do cache
query_cache = QueryCache(ttl_minutes=30, max_size=100)