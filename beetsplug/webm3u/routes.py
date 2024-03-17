import os
import re
import glob
from beets import config
from flask import Flask, Blueprint, current_app, send_from_directory, send_file, abort, render_template, request, url_for, jsonify, Response, stream_with_context
from pathlib import Path
from urllib.parse import quote, quote_plus
from werkzeug.utils import safe_join

MIMETYPE_HTML = 'text/html'
MIMETYPE_JSON = 'application/json'
MIMETYPE_MPEGURL = 'audio/mpegurl'

bp = Blueprint('webm3u_bp', __name__, template_folder='templates')

_format_regex = re.compile(r'\$[a-z0-9_]+')

@bp.route('/playlists/index.m3u')
def playlist_index():
    uri_format = request.args.get('uri-format')
    playlist_dir = playlist_provider().dir
    playlists = glob.glob(os.path.join(playlist_dir, "**.m3u8"))
    playlists += glob.glob(os.path.join(playlist_dir, "**.m3u"))
    playlists.sort()
    q = ''
    if uri_format:
        q = f"?uri-format={quote_plus(uri_format)}"
    lines = [_m3u_line(path, q) for path in playlists]
    return f"#EXTM3U\n{''.join(lines)}"

@bp.route('/playlists/', defaults={'path': ''})
@bp.route('/playlists/<path:path>')
def playlists(path):
    playlist_dir = playlist_provider().dir
    return _serve_files('playlists.html', 'Playlists', playlist_dir, path, _filter_m3u_files, _send_playlist, _playlist_info)

@bp.route('/audio/', defaults={'path': ''})
@bp.route('/audio/<path:path>')
def audio(path):
    root_dir = config['directory'].get()
    return _serve_files('files.html', 'Audio files', root_dir, path, _filter_none, send_file, _file_info)

def _m3u_line(filepath, query):
    title = Path(os.path.basename(filepath)).stem
    playlist_dir = playlist_provider().dir
    uri = _item_url('playlists', filepath, playlist_dir)
    return f'#EXTINF:0,{title}\n{uri}{query}\n'

def _send_playlist(filepath):
    provider = playlist_provider()
    relpath = os.path.relpath(filepath, provider.dir)
    playlist = provider.playlist(relpath)
    return Response(stream_with_context(_transform_playlist(playlist)), mimetype=MIMETYPE_MPEGURL)

def playlist_provider():
    return current_app.config['playlist_provider']

def _transform_playlist(playlist):
    music_dir = os.path.normpath(config['directory'].get())
    playlist_dir = playlist_provider().dir
    uri_format = request.args.get('uri-format')
    skipped = False

    yield '#EXTM3U\n'
    for item in playlist.items():
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

def _serve_files(tpl, title, root_dir, path, filter, handler, infofn):
    abs_path = safe_join(root_dir, path)
    if not os.path.exists(abs_path):
        return abort(404)
    if os.path.isfile(abs_path):
        return handler(abs_path)
    else:
        f = _files(abs_path, filter, infofn)
        dirs = _directories(abs_path)
        mimetypes = (MIMETYPE_JSON, MIMETYPE_HTML)
        mimetype = request.accept_mimetypes.best_match(mimetypes, MIMETYPE_JSON)
        if mimetype == MIMETYPE_HTML:
            return render_template(tpl,
                title=title,
                files=f,
                directories=dirs,
                humanize_size=_humanize_size,
                humanize_duration=_humanize_duration,
                quote=quote,
            )
        else:
            return jsonify({
                'directories': [{'name': d} for d in dirs],
                'files': f,
            })

def _files(dir, filter, infofn):
    l = [f for f in os.listdir(dir) if _is_file(dir, f) and filter(f)]
    l.sort()
    return [infofn(dir, f) for f in l]

def _file_info(dir, filename):
    st = os.stat(safe_join(dir, filename))
    return {
        'name': Path(filename).stem,
        'path': filename,
        'size': st.st_size,
    }

def _playlist_info(dir, filename):
    filepath = os.path.join(dir, filename)
    relpath = os.path.relpath(filepath, playlist_provider().dir)
    playlist = playlist_provider().playlist(relpath)
    return {
        'name': playlist.name,
        'path': playlist.id,
        'count': playlist.count,
        'duration': playlist.duration,
        'info': playlist.artists,
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

def _humanize_size(num):
    for unit in ("", "K", "M", "G", "T", "P", "E", "Z"):
        if abs(num) < 1000.0:
            return f"{num:.0f}{unit}B"
        num /= 1000.0
    return f"{num:.1f}YB"

minute = 60
hour = 60 * minute
day = 24 * hour

def _humanize_duration(seconds):
    days = seconds / day
    if days > 1:
        return '{:.0f}d'.format(days)
    hours = seconds / hour
    if hours > 1:
        return '{:.0f}h'.format(hours)
    minutes = seconds / minute
    if minutes > 1:
        return '{:.0f}m'.format(minutes)
    return '{:.0f}s'.format(seconds)
