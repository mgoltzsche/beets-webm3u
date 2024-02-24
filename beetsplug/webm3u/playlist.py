import re

def parse_playlist(filepath):
    # CAUTION: attribute values that contain ',' or ' ' are not supported
    extinf_regex = re.compile(r'^#EXTINF:([0-9]+)( [^,]+)?,[\s]*(.*)')
    with open(filepath, 'r', encoding='UTF-8') as file:
        linenum = 0
        item = PlaylistItem()
        while line := file.readline():
            line = line.rstrip()
            linenum += 1
            if linenum == 1:
                assert line == '#EXTM3U', 'File is not an EXTM3U playlist!'
                continue
            if len(line.strip()) == 0:
                continue
            m = extinf_regex.match(line)
            if m:
                item = PlaylistItem()
                duration = m.group(1)
                item.duration = int(duration)
                attrs = m.group(2)
                if attrs:
                    item.attrs = {k: v.strip('"') for k,v in [kv.split('=') for kv in attrs.strip().split(' ')]}
                else:
                    item.attrs = {}
                item.title = m.group(3)
                continue
            if line.startswith('#'):
                continue
            item.uri = line
            yield item
            item = PlaylistItem()

class PlaylistItem():
    def __init__(self):
        self.title = None
        self.duration = None
        self.uri = None
        self.attrs = None
