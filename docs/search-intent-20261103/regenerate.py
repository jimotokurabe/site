"""Render only the three reviewed pages using the normal production generators."""
import sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import build
from bus_pages import bus_page
from seo_markup import inject
prefs = {p: build.load_pref(ROOT / 'data' / f'{p}-menkyo-henno.json') for p in ('tokyo','kanagawa','hyogo')}
mm = json.loads((ROOT / build.MUNICIPAL_MOBILITY_DATA_PATH).read_text())
c = next(c for c in mm['cities'] if c['pref']=='tokyo' and c['municipality']=='hachioji')
peers = [o for o in mm['cities'] if o['pref']=='tokyo']
pages = {
 'tokyo-mobility/hachioji.html': build.mobility_city_page(c, {'scope':c['scope'],'level':c['level'],'page':'tokyo-mobility/hachioji.html','municipality':'hachioji'}, prefs['tokyo'], peers, {o['id']:o['scope'] for o in peers}, c['checked'], False, regional=False),
 'kanagawa-taxi.html': build.taxi_page(prefs['kanagawa'], False),
 'hyogo-bus.html': bus_page(prefs['hyogo'], prefs['hyogo']['bus'], False, build.shell, build.jdate),
}
for path, html in pages.items():
 (ROOT/path).write_text(inject(html,path))
 print(path)
