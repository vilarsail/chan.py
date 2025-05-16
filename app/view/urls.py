# coding:utf-8
import app.view.views as view

urlpatterns = [
    ('/alarm/hello', view.hello, {'methods': ['GET']}),
    ('/api/generate-image', view.generate_image, {'methods': ['POST']}),
    ('/api/get-recent-bsp', view.get_recent_bsp, {'methods': ['GET']}),
    ('/api/get-all-code-to-name-dict', view.get_all_code_to_name_dict, {'methods': ['GET']}),
]
