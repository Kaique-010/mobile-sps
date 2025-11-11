from django.urls import get_resolver

def list_urls():
    resolver = get_resolver()
    for pattern in resolver.url_patterns:
        try:
            print(pattern.pattern)
        except Exception:
            pass

if __name__ == "__main__":
    list_urls()
