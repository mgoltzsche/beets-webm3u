from flask import Flask
from beets.plugins import BeetsPlugin
from beets.ui import Subcommand, decargs
from optparse import OptionParser
from beetsplug.web import ReverseProxied
from beetsplug.webm3u.routes import bp


class PlaylistServerPlugin(BeetsPlugin):
    def __init__(self):
        super().__init__()
        self.config.add(
            {
                'host': '127.0.0.1',
                'port': 8339,
                'cors': '',
                'cors_supports_credentials': False,
                'reverse_proxy': False,
                'include_paths': False,
                'playlist_dir': None,
            }
        )

    def commands(self):
        p = OptionParser()
        p.add_option('-d', '--debug', action='store_true', default=False, help='debug mode')
        c = Subcommand('webm3u', parser=p, help='serve the playlists via HTTP')
        c.func = self._run_server
        return [c]

    def _run_server(self, lib, opts, args):
        create_app().run(
            host=self.config['host'].as_str(),
            port=self.config['port'].get(int),
            debug=opts.debug,
            threaded=True,
        )

    def _configure_app(self, app, lib):
        app.config['lib'] = lib
        app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
        app.config['INCLUDE_PATHS'] = self.config['include_paths']
        app.config['READONLY'] = True

        if self.config['cors']:
            self._log.info('Enabling CORS with origin {}', self.config['cors'])
            from flask_cors import CORS

            app.config['CORS_ALLOW_HEADERS'] = 'Content-Type'
            app.config['CORS_RESOURCES'] = {
                r'/*': {'origins': self.config['cors'].get(str)}
            }
            CORS(
                app,
                supports_credentials=self.config['cors_supports_credentials'].get(bool),
            )

        if self.config['reverse_proxy']:
            app.wsgi_app = ReverseProxied(app.wsgi_app)

def create_app():
    app = Flask(__name__)

    @app.route('/')
    def home():
        return '<html><body><ul><li><a href="playlists">Playlists</a></li><li><a href="media">Audio files</a></ul></body></html>'

    app.register_blueprint(bp)

    return app
