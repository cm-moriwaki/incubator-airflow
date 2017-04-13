# -*- coding: utf-8 -*-
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import socket

from flask import Flask
from flask_admin import Admin, base
from flask_cache import Cache
from flask_wtf.csrf import CsrfProtect

import airflow
from airflow import models
from airflow.settings import Session

from airflow.www.blueprints import ck, routes
from airflow import jobs
from airflow import settings
from airflow import configuration

csrf = CsrfProtect()


def create_app(config=None):
    app = Flask(__name__)
    app.secret_key = configuration.get('webserver', 'SECRET_KEY')
    app.config['LOGIN_DISABLED'] = not configuration.getboolean('webserver', 'AUTHENTICATE')
    timezone = configuration.get('core', 'TIMEZONE')

    csrf.init_app(app)

    # app.config = config
    airflow.load_login()
    airflow.login.login_manager.init_app(app)

    cache = Cache(
        app=app, config={'CACHE_TYPE': 'filesystem', 'CACHE_DIR': '/tmp'})

    app.register_blueprint(ck, url_prefix='/ck')
    app.register_blueprint(routes)
    app.jinja_env.add_extension("chartkick.ext.charts")

    with app.app_context():
        from airflow.www import views

        admin = Admin(
            app, name='CSA',
            static_url_path='/admin',
            index_view=views.HomeView(endpoint='', url='/admin', name=u"タスク"),
            template_mode='bootstrap3',
        )
        av = admin.add_view
        vs = views
        av(vs.Airflow(name=u'タスク', category=u'タスク'))

        # av(vs.QueryView(name='Ad Hoc Query', category="Data Profiling"))
        # av(vs.ChartModelView(
        #     models.Chart, Session, name="Charts", category="Data Profiling"))
        # av(vs.KnowEventView(
        #     models.KnownEvent,
        #     Session, name="Known Events", category="Data Profiling"))
        # av(vs.SlaMissModelView(
        #     models.SlaMiss,
        #     Session, name="SLA Misses", category=u"ブラウズ"))
        av(vs.VariableView(models.Variable, Session, name=u"変数", category=u"ブラウズ"))
        av(vs.FileToTableView(models.FileToTable, Session, name=u"連携ファイル", category=u"ブラウズ"))
        av(vs.CustomSqlView(models.CustomSql, Session, name=u"SQL", category=u"ブラウズ"))
        av(vs.CustomScriptView(models.CustomScript, Session, name=u"スクリプト", category=u"ブラウズ"))
        av(vs.TaskInstanceModelView(models.TaskInstance, Session, name=u"実行履歴", category=u"ログ"))
        # av(vs.LogModelView(
        #     models.Log, Session, name=u"ログ", category=u"ブラウズ"))
        # av(vs.JobModelView(
        #     jobs.BaseJob, Session, name="Jobs", category=u"ブラウズ"))
# av(vs.PoolModelView(
#     models.Pool, Session, name="Pools", category="Admin"))
# av(vs.ConfigurationView(
#     name='Configuration', category="Admin"))
# av(vs.UserModelView(
#     models.User, Session, name="Users", category="Admin"))
# av(vs.ConnectionModelView(
#     models.Connection, Session, name="Connections", category="Admin"))

# admin.add_link(base.MenuLink(
#     category='Docs', name='Documentation',
#     url='http://pythonhosted.org/airflow/'))
# admin.add_link(
#     base.MenuLink(category='Docs',
#                   name='Github', url='https://github.com/airbnb/airflow'))

    # av(vs.DagRunModelView(
    #     models.DagRun, Session, name="DAG Runs", category=u"ブラウズ"))
    av(vs.DagModelView(models.DagModel, Session, name=None))
    # Hack to not add this view to the menu
    admin._menu = admin._menu[:-1]

    def integrate_plugins():
        """Integrate plugins to the context"""
        from airflow.plugins_manager import (
            admin_views, flask_blueprints, menu_links)
        for v in admin_views:
            admin.add_view(v)
        for bp in flask_blueprints:
            app.register_blueprint(bp)
        for ml in menu_links:
            admin.add_link(ml)

    integrate_plugins()

    @app.context_processor
    def jinja_globals():
        return {
            'hostname': socket.gethostname(),
            'timezone': timezone,
        }

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        settings.Session.remove()

    return app

app = None


def cached_app(config=None):
    global app
    if not app:
        app = create_app(config)
    return app
