"""Fresh, local acceptance check with a real render and preserved current file."""
import json
import struct
import time
from tests.e2e import api, generate, audit, ROOT, COMMAND

def main():
    current = ROOT/'projects/current_project.json'
    previous = current.read_bytes() if current.exists() else None
    project = api('/demo')
    project['project_name'] = 'QA fresh Blender ' + time.strftime('%Y%m%d-%H%M%S')
    report = {'checked_at': time.strftime('%Y-%m-%d %H:%M:%S')}
    try:
        print('Generating fresh initial geometry...', flush=True)
        before = generate(project, False)
        report['before_geometry'] = audit(before, project, 'qa-fresh-initial')
        changed = api('/modify', {'command':COMMAND, 'project':project})
        assert len(changed['changes']) == 4
        print('Rendering fresh modified concept in Blender...', flush=True)
        after = generate(changed['project'], True)
        report['after_geometry'] = audit(after, changed['project'], 'qa-fresh-modified')
        png = (ROOT/'output'/after['id']/'preview.png').read_bytes()
        assert png[:8] == b'\x89PNG\r\n\x1a\n'
        assert struct.unpack('>II', png[16:24]) == (1600, 1000)
        assert len(png) > 10000
        print('Checking undo restores the original model...', flush=True)
        restored = generate(project, False)
        assert restored['id'] == before['id']
        assert json.loads(current.read_text()) == project
        report.update(result='PASS', before=before, after=after, undo=True)
        (ROOT/'output/qa-fresh-blender.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps({'result':'PASS', 'initial_seconds':before['seconds'], 'render_seconds':after['seconds'], 'render':after['preview_url']}), flush=True)
    finally:
        # Do not overwrite another user's concurrent save.
        if previous is not None and current.exists() and json.loads(current.read_text()).get('project_name') == project['project_name']:
            current.write_bytes(previous)

if __name__ == '__main__':
    main()
