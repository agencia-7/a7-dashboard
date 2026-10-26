import urllib.request, json, re, os

TOKEN    = os.environ['META_TOKEN']
ACCOUNTS = ['619334585395511', '1000257484054841']
GV       = 'v21.0'

# Clientes cujo ROAS é monitorado — altere apenas aqui quando houver adição/remoção
CLIENTS = {
    'EL CHAVO':   'El Chavo',
    'JULIAN':     "Julian's Grill",
    'QUINTAL':    'Quintal',
    'PICCOLIN':   'Piccolinos',
    'TOURO LOKO': 'Touro Loko',
    'WATERMANN':  'Watermann',
    'OFIR':       'Ofir',
}

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

def calc_roas_stats(preset):
    """Calcula ROAS por cliente e retorna máx, mín e média."""
    totals = {k: {'spend': 0.0, 'revenue': 0.0} for k in CLIENTS}
    for ac in ACCOUNTS:
        url = (f'https://graph.facebook.com/{GV}/act_{ac}/insights'
               f'?level=campaign&fields=campaign_name,spend,action_values'
               f'&date_preset={preset}&access_token={TOKEN}&limit=500')
        d = req(url)
        for row in (d.get('data') or []):
            name = (row.get('campaign_name') or '').upper()
            for kw in CLIENTS:
                if kw in name:
                    totals[kw]['spend']   += float(row.get('spend', 0))
                    totals[kw]['revenue'] += action_val(row.get('action_values'), 'omni_purchase')
                    break  # evita dupla contagem
    vals = [t['revenue'] / t['spend'] for t in totals.values() if t['spend'] > 0]
    if not vals:
        return {'max': '\u2014', 'min': '\u2014', 'avg': '\u2014'}
    return {
        'max': fmt_br(max(vals), 2),
        'min': fmt_br(min(vals), 2),
        'avg': fmt_br(sum(vals) / len(vals), 2),
    }

results = {}
for key, preset in [('hoje','today'), ('7d','last_7d'), ('30d','last_30d')]:
    a1 = account_insights(ACCOUNTS[0], preset)
    a2 = account_insights(ACCOUNTS[1], preset)
    roas = calc_roas_stats(preset)
    results[key] = dict(
        spend       = fmt_br(a1['spend']       + a2['spend'],       2),
        revenue     = fmt_br(a1['revenue']     + a2['revenue'],     2),
        sales       = fmt_br(a1['sales']       + a2['sales'],       0),
        reach       = fmt_br(a1['reach']       + a2['reach'],       0),
        impressions = fmt_br(a1['impressions'] + a2['impressions'], 0),
        clicks      = fmt_br(a1['clicks']      + a2['clicks'],      0),
        roas_max    = roas['max'],
        roas_min    = roas['min'],
        roas_avg    = roas['avg'],
    )
    print(f"{key}: spend={results[key]['spend']} roas_avg={results[key]['roas_avg']}")

h = results['hoje']; d7 = results['7d']; d30 = results['30d']
new_defaults = f"""const DEFAULTS = {{
  hoje: {{ spend: '{h["spend"]}', revenue: '{h["revenue"]}', sales: '{h["sales"]}', reach: '{h["reach"]}', impressions: '{h["impressions"]}', clicks: '{h["clicks"]}', roas_max: '{h["roas_max"]}', roas_min: '{h["roas_min"]}', roas_avg: '{h["roas_avg"]}' }},
  '7d': {{ spend: '{d7["spend"]}', revenue: '{d7["revenue"]}', sales: '{d7["sales"]}', reach: '{d7["reach"]}', impressions: '{d7["impressions"]}', clicks: '{d7["clicks"]}', roas_max: '{d7["roas_max"]}', roas_min: '{d7["roas_min"]}', roas_avg: '{d7["roas_avg"]}' }},
  '30d':{{ spend: '{d30["spend"]}', revenue: '{d30["revenue"]}', sales: '{d30["sales"]}', reach: '{d30["reach"]}', impressions: '{d30["impressions"]}', clicks: '{d30["clicks"]}', roas_max: '{d30["roas_max"]}', roas_min: '{d30["roas_min"]}', roas_avg: '{d30["roas_avg"]}' }},
}};"""

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

html_new = re.sub(r'const DEFAULTS = \{.*?\};', new_defaults, html, flags=re.DOTALL)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html_new)

print("index.html atualizado com sucesso")
