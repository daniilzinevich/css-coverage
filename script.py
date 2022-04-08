import os
import json

from sourcemap import SourceMap

files = dict()

for file in os.listdir():
  if file.endswith('.json'):
    with open(file) as f:
      read_data = f.read()
      as_json = json.loads(read_data)
      for file in as_json:
        if file['url'] in files:
          files[file['url']]['ranges'] += file['ranges']
        else:
          files[file['url']] = { 'ranges': file['ranges'], 'text': file['text'] }

for file_name, stats in files.items():
  sourcemap = None
  if os.path.exists(file_name.split('/')[-1] + '.map'):
    with open(file_name.split('/')[-1] + '.map') as f:
      read_data = f.read()
      sourcemap = SourceMap.from_json(json.loads(read_data))
      print(file_name.split('/')[-1], sourcemap.entries[(0, 0)].source)
  else:
    print(file_name.split('/')[-1] + ' has no map file')

  with open(file_name.split('/')[-1] + '.cov.html', 'w') as f:
    total = 0
    uncovered = 0
    start_num = 0
    last_source = None
    sources = dict()

    f.write('<!DOCTYPE html>')
    f.write('<html>')
    f.write('<head><link rel="stylesheet" href="./style.css"></head>')
    f.write('<body><div>')


    for index, line in enumerate(stats['text'].split('\n')):
      start_num += len(line) + 1
      in_range = next((
          True for range in stats['ranges'] \
          if start_num > range['start'] and \
          start_num <= range['end'] + 1
        ), False)

      source = None
      try:
        source = sourcemap.entries[index, 0].source
        if source in sources:
          sources[source] += 1 if in_range else 0
        else:
          sources[source] = 1 if in_range else 0
      except:
        pass

      f.write(f'<div class="{ "covered" if in_range else "" }">')
      f.write(f'<span class="number">{index}</span> <code>{line.replace(" ", "&nbsp;")}</code>')
      if (source is not None and source != last_source):
        f.write(f'<span class="source">{source}</span>')
        last_source = source
      f.write('</div>\n')
      

      total += 1
      if not in_range: uncovered += 1
    
    f.write('</div><div class="summary"><div>')
    f.write(f'<div>Total lines: {total}</div>')
    f.write(f'<div>Covered lines: {total - uncovered}</div>')
    f.write(f'<div>Uncovered lines: {uncovered}</div>')
    if sourcemap is not None:
      f.write('<span class="tip">hover to display modules isights</span></div>')
      f.write('<div class="modules">')

      for source, stats in sources.items():
        is_node = 'node_modules/' in source
        source_clear = source.replace('webpack:///', '').lstrip('./')
        if is_node: source_clear = source_clear.replace('node_modules/', '')
        source_clear = '<span class="path">' + \
          '</span><span class="path">'.join(source_clear.split('/')) + \
          '</span>'

        f.write(f'<div class="module">{source_clear} <span class="total { "danger" if stats == 0 else "" }">{stats}</span></div>')    
    f.write('</div></div>')

    f.write('</body>')
    f.write('</html>')
