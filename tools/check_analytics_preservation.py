"""Compare published content to the audit baseline; no data/site mutations."""
import io,json,subprocess,tarfile
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Content(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True);self.skip=0;self.text=[];self.links=[];self.ids=[];self.feed(html)
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag in ('script','style'):self.skip+=1
        if tag=='a' and 'href' in attrs:self.links.append(attrs['href'])
        if 'id' in attrs:self.ids.append(attrs['id'])
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.skip=max(0,self.skip-1)
    def handle_data(self,value):
        if not self.skip and value.strip():self.text.append(' '.join(value.split()))
issues=[];count=0;data_count=0
archive=subprocess.check_output(['git','archive','988173439fde62f4a8d948e42f70232ef551b2a7'],cwd=ROOT)
with tarfile.open(fileobj=io.BytesIO(archive)) as t:
    for item in t:
        if not item.isfile():continue
        current=ROOT/item.name
        if item.name.startswith(('data/','assets/outing-supports/')):
            data_count+=1
            if not current.exists() or current.read_bytes()!=t.extractfile(item).read():issues.append([item.name,'data changed'])
        elif item.name.endswith('.html'):
            old=Content(t.extractfile(item).read().decode());new=Content(current.read_text());count+=1
            if old.links!=new.links:issues.append([item.name,'links changed'])
            if set(old.ids)!=set(new.ids):issues.append([item.name,'IDs changed'])
            if item.name!='privacy.html' and old.text!=new.text:issues.append([item.name,'visible text changed'])
result={'baseline':'98817343','html_pages':count,'data_and_catalog_files':data_count,'allowed_text_change':['privacy.html'],'issues':issues}
print(json.dumps(result,ensure_ascii=False,indent=2))
raise SystemExit(bool(issues))
