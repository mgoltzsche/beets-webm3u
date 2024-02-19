import os
from flask import Flask, Blueprint, send_from_directory, send_file, abort
from beets import config


bp = Blueprint('webm3u_bp', __name__, template_folder='templates')

@bp.route('/playlists/', defaults={'path': ''})
@bp.route('/playlists/<path:path>')
def index_page(path):
    root_dir = config['webm3u']['playlist_dir'].get()
    if not root_dir:
        root_dir = config['smartplaylist']['playlist_dir'].get()
    abs_path = os.path.join(root_dir, path)
    _check_path(root_dir, abs_path)
    if not os.path.exists(abs_path):
        return abort(404)
    if os.path.isfile(abs_path):
        # TODO: transform item URIs within playlist
        return send_file(abs_path)
    else:
        # Generate html/json directory listing
        return 'playlist dir'
    #return send_from_directory(root_dir, path, as_attachment=True)

def _check_path(root_dir, path):
    path = os.path.normpath(path)
    root_dir = os.path.normpath(root_dir)
    if path != root_dir and not path.startswith(root_dir+os.sep):
        raise Exception('request path {} is outside the root directory {}'.format(path, root_dir))
