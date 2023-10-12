import os, io, csv


IN_PATH = os.path.join(os.getcwd(), 'TAXRATES_ZIP5')
OUT_FPATH = os.path.join('pkdiagram', 'sales_tax_rates.py')
print('Writing %s' % OUT_FPATH)
zips = {}

# Tax rates from Avalara:
# https://www.avalara.com/taxrates/en/download-tax-tables.html
for name in os.listdir(IN_PATH):
    if not name.endswith('.csv'):
        continue
    fpath = os.path.join(IN_PATH, name)
    with io.open(fpath, 'r') as f:
        lines = csv.reader(f)
        for i, row in enumerate(lines):
            if i > 0:
                entry = {
                    'state': row[0],
                    'zip': int(row[1]),
                    'name': row[2],
                    'stateRate': float(row[3]),
                    'estimatedCombinedRate': float(row[4]),
                    'estimatedCountyRate': float(row[5]),
                    'estimatedCityRate': float(row[6]),
                    'estimatedSpecialRate': float(row[7]),
                    'riskLevel': int(row[8])
                }
                zips[entry['zip']] = entry


with open(OUT_FPATH, 'w') as f:
    lines = []
    lines.append('zips = {')
    for k in sorted(zips.keys()):
        lines.append("    '%s': %f," % (k, zips[k]['estimatedCombinedRate']))
    lines.append('}')
    f.writelines(lines)

