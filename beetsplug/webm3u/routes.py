import os
import re
import glob
from flask import Flask, Blueprint, current_app, send_from_directory, send_file, abort, render_template, request, url_for, jsonify, Response, stream_with_context
from beets import config
from pathlib import Path
from urllib.parse import quote, quote_plus
from beetsplug.webm3u.playlist import parse_playlist

MIMETYPE_HTML = 'text/html'
MIMETYPE_JSON = 'application/json'
MIMETYPE_MPEGURL = 'audio/mpegurl'

bp = Blueprint('webm3u_bp', __name__, template_folder='templates')

_format_regex = re.compile(r'\$[a-z0-9_]+')

@bp.route('/playlists/index.m3u8')
def playlist_index():
    uri_format = request.args.get('uri-format')
    root_dir = _playlist_dir()
    playlists = glob.glob(os.path.join(root_dir, "**.m3u8"))
    playlists.sort()
    q = ''
    if uri_format:
        q = f"?uri-format={quote_plus(uri_format)}"
    lines = [_m3u_line(path, q) for path in playlists]
    return f"#EXTM3U\n{''.join(lines)}"

@bp.route('/playlists/', defaults={'path': ''})
@bp.route('/playlists/<path:path>')
def playlists(path):
    root_dir = _playlist_dir()
    return _serve_files('Playlists', root_dir, path, _filter_m3u_files, _send_playlist)

@bp.route('/audio/', defaults={'path': ''})
@bp.route('/audio/<path:path>')
def audio(path):
    root_dir = config['directory'].get()
    return _serve_files('Audio files', root_dir, path, _filter_none, send_file)

def _m3u_line(filepath, query):
    title = Path(os.path.basename(filepath)).stem
    uri = _item_url('playlists', filepath, _playlist_dir())
    return f'#EXTINF:0,{title}\n{uri}{query}\n'

def _playlist_dir():
    root_dir = config['webm3u']['playlist_dir'].get()
    if not root_dir:
        return config['smartplaylist']['playlist_dir'].get()
    return root_dir

def _send_playlist(filepath):
    return Response(stream_with_context(_transform_playlist(filepath)), mimetype=MIMETYPE_MPEGURL)

def _transform_playlist(filepath):
    music_dir = os.path.normpath(config['directory'].get())
    playlist_dir = os.path.dirname(filepath)
    uri_format = request.args.get('uri-format')
    skipped = False

    yield '#EXTM3U\n'
    for item in parse_playlist(filepath):
        item_uri = item.uri
        if item_uri.startswith('./') or item_uri.startswith('../'):
            item_uri = os.path.join(playlist_dir, item_uri)
        item_uri = os.path.normpath(item_uri)
        item_uri = _item_url('audio', item_uri, music_dir)
        if uri_format:
            item.attrs['url'] = item_uri
            try:
                item_uri = _format_regex.sub(_format(item.attrs), uri_format)
            except KeyError as e:
                if not skipped:
                    skipped = True
                    msg = f"Skipping playlist item(s) because URI format refers to missing key {e}"
                    current_app.logger.warning(msg)
                continue
        yield f"#EXTINF:{item.duration},{item.title}\n{item_uri}\n"

def _item_url(endpoint, filepath, root_dir):
    item_uri = os.path.relpath(filepath, root_dir)
    item_uri = url_for(f'webm3u_bp.{endpoint}', path=item_uri)
    return f"{request.host_url.rstrip('/')}{item_uri}"

def _format(attrs):
    return lambda m: attrs[m.group(0)[1:]]

def _filter_m3u_files(filename):
    return filename.endswith('.m3u') or filename.endswith('.m3u8')

def _filter_none(filename):
    return True

def _serve_files(title, root_dir, path, filter, handler):
    abs_path = os.path.join(root_dir, path)
    _check_path(root_dir, abs_path)
    if not os.path.exists(abs_path):
        return abort(404)
    if os.path.isfile(abs_path):
        return handler(abs_path)
    else:
        f = _files(abs_path, filter)
        dirs = _directories(abs_path)
        mimetypes = (MIMETYPE_JSON, MIMETYPE_HTML)
        mimetype = request.accept_mimetypes.best_match(mimetypes, MIMETYPE_JSON)
        if mimetype == MIMETYPE_HTML:
            return render_template('list.html',
                title=title,
                files=f,
                directories=dirs,
                humanize=_humanize_size,
                quote=quote,
            )
        else:
            return jsonify({
                'directories': [{'name': d} for d in dirs],
                'files': f,
            })

def _files(dir, filter):
    l = [f for f in os.listdir(dir) if _is_file(dir, f) and filter(f)]
    l.sort()
    return [_file_dto(dir, f) for f in l]

def _file_dto(dir, filename):
    st = os.stat(os.path.join(dir, filename))
    return {
        'name': Path(filename).stem,
        'path': filename,
        'size': st.st_size,
    }

def _is_file(dir, filename):
    f = os.path.join(dir, filename)
    return os.path.isfile(f)

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
        raise Exception(f"request path {path} is outside the root directory {root_dir}")

def _humanize_size(num):
    for unit in ("", "K", "M", "G", "T", "P", "E", "Z"):
        if abs(num) < 1000.0:
            return f"{num:.0f}{unit}B"
        num /= 1000.0
    return f"{num:.1f}YB"
