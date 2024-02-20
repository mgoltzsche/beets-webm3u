import os
from flask import Flask, Blueprint, send_from_directory, send_file, abort, render_template, request, jsonify
from beets import config
from pathlib import Path

MIMETYPE_HTML = 'text/html'
MIMETYPE_JSON = 'application/json'

bp = Blueprint('webm3u_bp', __name__, template_folder='templates')

@bp.route('/playlists/', defaults={'path': ''})
@bp.route('/playlists/<path:path>')
def playlists(path):
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
        pl = _playlists(abs_path)
        dirs = _directories(abs_path)
        mimetypes = (MIMETYPE_JSON, MIMETYPE_HTML)
        mimetype = request.accept_mimetypes.best_match(mimetypes, MIMETYPE_JSON)
        if mimetype == MIMETYPE_HTML:
            return render_template('playlists.html',
                path=path,
                playlists=pl,
                directories=dirs,
                humanize=_humanize_size,
            )
        else:
            return jsonify({
                'directories': [{'name': d} for d in dirs],
                'playlists': pl,
            })

@bp.route('/music/', defaults={'path': ''})
@bp.route('/music/<path:path>')
def music(path):
    root_dir = config['directory'].get()
    return send_from_directory(root_dir, path)

def _playlists(dir):
    l = [f for f in os.listdir(dir) if _is_playlist(dir, f)]
    l.sort()    
    return [_playlist_dto(dir, f) for f in l]

def _playlist_dto(dir, filename):
    st = os.stat(os.path.join(dir, filename))
    return {
        'name': Path(filename).stem,
        'path': filename,
        'size': st.st_size,
    }

def _is_playlist(dir, filename):
    f = os.path.join(dir, filename)
    return os.path.isfile(f) and (f.endswith('.m3u') or f.endswith('.m3u8'))

def _directories(dir):
    l = [d for d in os.listdir(dir) if os.path.isdir(_join(dir, d))]
    l.sort()
    return l

def _join(dir, filename):
    return os.path.join(dir, filename)

def _check_path(root_dir, path):
    path = os.path.normpath(path)
    root_dir = os.path.normpath(root_dir)
    if path != root_dir and not path.startswith(root_dir+os.sep):
        raise Exception('request path {} is outside the root directory {}'.format(path, root_dir))

def _humanize_size(num):
    suffix = 'B'
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"
