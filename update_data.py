import urllib.request, json, re, os

TOKEN    = os.environ['META_TOKEN']
ACCOUNTS = ['619334585395511', '1000257484054841']
KEYWORDS = ['Julian', 'Quintal', 'Piccolin', 'Ofir', 'Trilha']
GV       = 'v21.0'

def fmt_br(num, dec=0):
    if not num or num == 0:
        return '0'
    if dec > 0:
        s = f'{float(num):.{dec}f}'.split('.')
        s[0] = '{:,}'.format(int(s[0])).replace(',', '.')
        return s[0] + ',' + s[1]
    return '{:,}'.format(round(float(num))).replace(',', '.')

def req(url):
    r = urllib.request.Request(url, headers={'User-Agent': 'A7Bot'})
    with urllib.request.urlopen(r) as resp:
        return json.loads(resp.read())

def action_val(arr, t):
    for a in (arr or []):
        if a['action_type'] == t:
            return float(a['value'])
    return 0

def account_insights(ac, preset):
    url = (f'https://graph.facebook.com/{GV}/act_{ac}/insights'
           f'?level=account&fields=spend,reach,impressions,actions,action_values'
           f'&date_preset={preset}&access_token={TOKEN}')
    d = req(url)
    if 'error' in d:
        raise Exception(d['error']['message'])
    row = (d.get('data') or [{}])[0]
    return dict(
        spend       = float(row.get('spend', 0)),
        reach       = int(row.get('reach', 0)),
        impressions = int(row.get('impressions', 0)),
        sales       = action_val(row.get('actions'), 'omni_purchase'),
        revenue     = action_val(row.get('action_values'), 'omni_purchase'),
        clicks      = action_val(row.get('actions'), 'link_click'),
    )

def calc_roas(preset):
    ts, tr = 0.0, 0.0
    for ac in ACCOUNTS:
        url = (f'https://graph.facebook.com/{GV}/act_{ac}/insights'
               f'?level=campaign&fields=campaign_name,spend,action_values'
               f'&date_preset={preset}&access_token={TOKEN}&limit=500')
        d = req(url)
        for row in (d.get('data') or []):
            if any(k in (row.get('campaign_name') or '') for k in KEYWORDS):
                ts += float(row.get('spend', 0))
                tr += action_val(row.get('action_values'), 'omni_purchase')
    return '—' if ts == 0 else fmt_br(tr / ts, 2)

results = {}
for key, preset in [('hoje','today'), ('7d','last_7d'), ('30d','last_30d')]:
    a1 = account_insights(ACCOUNTS[0], preset)
    a2 = account_insights(ACCOUNTS[1], preset)
    results[key] = dict(
        spend       = fmt_br(a1['spend']       + a2['spend'],       2),
        revenue     = fmt_br(a1['revenue']     + a2['revenue'],     2),
        sales       = fmt_br(a1['sales']       + a2['sales'],       0),
        reach       = fmt_br(a1['reach']       + a2['reach'],       0),
        impressions = fmt_br(a1['impressions'] + a2['impressions'], 0),
        clicks      = fmt_br(a1['clicks']      + a2['clicks'],      0),
        roas        = calc_roas(preset),
    )
    print(f"{key}: spend={results[key]['spend']}")

h = results['hoje']; d7 = results['7d']; d30 = results['30d']
new_defaults = f"""const DEFAULTS = {{
  hoje: {{ spend: '{h['spend']}', revenue: '{h['revenue']}', sales: '{h['sales']}', reach: '{h['reach']}', impressions: '{h['impressions']}', clicks: '{h['clicks']}', roas: '{h['roas']}' }},
  '7d': {{ spend: '{d7['spend']}', revenue: '{d7['revenue']}', sales: '{d7['sales']}', reach: '{d7['reach']}', impressions: '{d7['impressions']}', clicks: '{d7['clicks']}', roas: '{d7['roas']}' }},
  '30d':{{ spend: '{d30['spend']}', revenue: '{d30['revenue']}', sales: '{d30['sales']}', reach: '{d30['reach']}', impressions: '{d30['impressions']}', clicks: '{d30['clicks']}', roas: '{d30['roas']}' }},
}};"""

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

html_new = re.sub(r'const DEFAULTS = \{.*?\};', new_defaults, html, flags=re.DOTALL)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html_new)

print("index.html atualizado com sucesso")
