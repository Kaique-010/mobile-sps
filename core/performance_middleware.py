import time
import logging
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

# Configure logger to respect DEBUG setting
performance_logger = logging.getLogger('performance')
if settings.DEBUG:
    performance_logger.setLevel(logging.INFO)
else:
    performance_logger.setLevel(logging.WARNING)  # Only show slow requests

class PerformanceMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._start_time = time.time()
        request._middleware_times = {}
        if settings.DEBUG:
            performance_logger.info(f"🚀 INÍCIO REQUISIÇÃO: {request.method} {request.path}")
        
    def process_response(self, request, response):
        if hasattr(request, '_start_time'):
            total_time = (time.time() - request._start_time) * 1000
            
            # Log detalhado da performance apenas em DEBUG
            if settings.DEBUG:
                performance_logger.info(f"⏱️  TEMPO TOTAL: {total_time:.2f}ms - {request.method} {request.path}")
            
            # Log dos tempos de cada middleware se disponível
            if hasattr(request, '_middleware_times') and settings.DEBUG:
                for middleware, duration in request._middleware_times.items():
                    performance_logger.info(f"   📊 {middleware}: {duration:.2f}ms")
            
            # Alertar apenas requisições MUITO lentas (>10s) em produção
            if settings.DEBUG and total_time > 1000:  # Em DEBUG: >1s
                performance_logger.warning(f"🐌 REQUISIÇÃO LENTA: {total_time:.2f}ms - {request.path}")
            elif not settings.DEBUG and total_time > 10000:  # Em produção: >10s
                performance_logger.warning(f"🐌 REQUISIÇÃO MUITO LENTA: {total_time:.2f}ms - {request.path}")
                
        return response