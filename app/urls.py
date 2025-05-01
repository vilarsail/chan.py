    # common API
from app.demo.urls import urlpatterns as demo_urls

pattern_map = {
    'alarm': demo_urls
}


def register_urlpatterns(app):
    for prefix in pattern_map:
        for pattern in pattern_map[prefix]:
            assert len(pattern) > 1
            options = {}
            if len(pattern) > 2:
                rule, view_func, options = pattern
            else:
                rule, view_func = pattern
            view_name = prefix + '.' + view_func.__name__
            app.add_url_rule(rule, endpoint=view_name, view_func=view_func, **options)
