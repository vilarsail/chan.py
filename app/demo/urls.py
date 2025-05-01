# coding:utf-8
import app.demo.views as view

urlpatterns = [
    ('/alarm/hello', view.hello, {'methods': ['GET']}),
]
