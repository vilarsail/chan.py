# coding:utf-8
import app.view.views as view

urlpatterns = [
    ('/alarm/hello', view.hello, {'methods': ['GET']}),
    ('/api/generate-image', view.generate_image, {'methods': ['POST']}),
]
