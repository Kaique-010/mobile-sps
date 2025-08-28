import time
import logging
from django.utils.deprecation import MiddlewareMixin

# Configurar logger específico para performance
performance_logger = logging.getLogger('performance')
performance_logger.setLevel(logging.INFO)

class PerformanceMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._start_time = time.time()
        request._middleware_times = {}
        performance_logger.info(f"🚀 INÍCIO REQUISIÇÃO: {request.method} {request.path}")
        
    def process_response(self, request, response):
        if hasattr(request, '_start_time'):
            total_time = (time.time() - request._start_time) * 1000
            
            # Log detalhado da performance
            performance_logger.info(f"⏱️  TEMPO TOTAL: {total_time:.2f}ms - {request.method} {request.path}")
            
            # Log dos tempos de cada middleware se disponível
            if hasattr(request, '_middleware_times'):
                for middleware, duration in request._middleware_times.items():
                    performance_logger.info(f"   📊 {middleware}: {duration:.2f}ms")
            
            # Alertar se muito lento
            if total_time > 1000:  # > 1 segundo
                performance_logger.warning(f"🐌 REQUISIÇÃO LENTA: {total_time:.2f}ms - {request.path}")
                
        return response