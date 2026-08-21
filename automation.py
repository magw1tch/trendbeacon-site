from urllib.request import Request,urlopen
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote
import datetime,json,re,html

def fetch(url):
    req=Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; TrendBeaconBot/1.0; +https://trendbeacon.co.uk)'})
    with urlopen(req,timeout=40) as r:return r.read()
def local(tag):return tag.split('}',1)[-1]
def text(node,name):
    if node is None:return ''
    for x in list(node):
        if local(x.tag)==name:return (x.text or '').strip()
    return ''
def items(raw):return [x for x in ET.fromstring(raw).iter() if local(x.tag)=='item']
def slugify(s):return re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-')[:80]
def volume_number(s):
    m=re.search(r'([\d,.]+)\s*([KMB]?)',s.upper())
    if not m:return 0
    n=float(m.group(1).replace(',','')); mult={'K':1_000,'M':1_000_000,'B':1_000_000_000}.get(m.group(2),1)
    return int(n*mult)

PRODUCT_RULES={
 'Technology':['printer','camera','charger','phone','tablet','laptop','headphone','earbud','smartwatch','projector','carplay','gadget','device'],
 'Home & Garden':['air conditioner','cooling','cleaner','vacuum','garden','feeder','kitchen','storage','lamp','fan','mattress'],
 'Fitness':['walking pad','treadmill','fitness','gym','recovery','massage','bottle'],
 'Motoring':['dash cam','carplay','car accessory','tyre','vehicle','car '],
 'Pets':['pet ','dog ','cat ','bird feeder','aquarium'],
 'Seasonal':['christmas','halloween','summer','winter','gift']}
def category(title):
    t=' '+title.lower()+' '
    for cat,keys in PRODUCT_RULES.items():
        if any(k in t for k in keys):return cat
    return 'Consumer Trends'
def is_product(title):return category(title)!='Consumer Trends'
def stage(vol):
    if vol>=200000:return 'Explosive'
    if vol>=50000:return 'Hot'
    if vol>=10000:return 'Rising'
    return 'Emerging'
def amazon_query(title):
    clean=re.sub(r'\b(uk|trend|trending|viral|best|2026)\b','',title,flags=re.I)
    return re.sub(r'\s+',' ',clean).strip() or title

def report_html(x,updated):
    title=html.escape(x['title']);cat=html.escape(x['category']);stage_name=html.escape(x['stage']);volume=html.escape(x['search_volume']);
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Why Is {title} Trending? | TrendBeacon</title><meta name="description" content="Explore why {title} is trending, the current search signal and related product opportunities."><link rel="stylesheet" href="../style.css"></head><body><main class="generated-report"><a href="../index.html" style="color:#7cff5b">← TrendBeacon</a><p class="eyebrow">AUTOMATED TREND REPORT</p><h1>Why Is {title} Trending?</h1><p class="report-meta">Category: {cat} • Stage: {stage_name} • Search signal: {volume} • {updated}</p><h2>Current signal</h2><p>{title} appeared in the UK Google Trends feed with an approximate search-volume label of {volume}. TrendBeacon categorised the topic as {cat} and assigned the stage {stage_name} using transparent volume thresholds.</p><h2>Products and opportunities</h2><p>Where the topic represents a consumer product, TrendBeacon provides an Amazon UK search rather than claiming live pricing, ratings or availability.</p><p><a class="product-row" style="display:block;color:#071007;background:#7cff5b;text-decoration:none;border-radius:9px" href="https://www.amazon.co.uk/s?k={quote(x['amazon_query'])}&tag=tradebeacon-21" rel="nofollow sponsored noopener">Search Amazon UK →</a></p><h2>Source and limitations</h2><p>The search signal comes from Google Trends RSS. Automated classification can be imperfect, so TrendBeacon presents the source, stage logic and update date clearly.</p></main></body></html>"""

old={}
try:old=json.loads(Path('trend-data.json').read_text())
except:pass
raw=fetch('https://trends.google.com/trending/rss?geo=GB')
all_trends=[]
for it in items(raw)[:30]:
    title=text(it,'title');traffic=text(it,'approx_traffic') or 'Rising';
    if not title:continue
    vol=volume_number(traffic);cat=category(title)
    news_nodes=[x for x in list(it) if local(x.tag)=='news_item'];desc=text(news_nodes[0],'news_item_title') if news_nodes else ''
    all_trends.append({'title':title,'category':cat,'stage':stage(vol),'signal':desc or 'Current UK search signal','search_volume':traffic,'volume_number':vol,'amazon_query':amazon_query(title) if is_product(title) else '', 'slug':slugify(title),'source':'Google Trends UK'})
product_trends=[x for x in all_trends if x['category']!='Consumer Trends']
# Use live product trends first, then retain clearly labelled editorial seeds to prevent emptiness.
seeds=old.get('trending',[])
seen={x['title'].lower() for x in product_trends}
combined=product_trends+[dict(x,signal=x.get('signal','Editorial watchlist')) for x in seeds if x.get('title','').lower() not in seen]
combined=combined[:12]
rising=[x for x in combined if x['stage'] in ('Emerging','Rising')][:8]
now=datetime.datetime.now(datetime.timezone.utc);display=now.strftime('Updated %d %b %Y, %H:%M UTC')
Path('reports').mkdir(exist_ok=True)
for x in combined:Path('reports',x['slug']+'.html').write_text(report_html(x,display),encoding='utf-8')
data={'updated_at':now.isoformat(),'updated_display':display,'trending':combined,'rising':rising,'source':'Google Trends UK RSS','stage_thresholds':{'Emerging':'under 10K','Rising':'10K+','Hot':'50K+','Explosive':'200K+'}}
Path('trend-data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print('Generated',len(combined),'trends and',len(combined),'reports')
