import argparse
import importlib
import json
import os
import sys
import time
import traceback


_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)


def _severity_rank(name):
    order = {
        'none': 0,
        'low': 1,
        'medium': 2,
        'high': 3,
        'critical': 4,
    }
    return order.get((name or '').lower().strip(), 0)


def _safe_makedirs(p):
    if not p:
        return
    os.makedirs(p, exist_ok=True)


def _coerce_bool(v):
    if isinstance(v, bool):
        return v
    s = (v or '').strip().lower()
    return s in ('1', 'true', 'yes', 'y', 'on')


def _load_rule_meta():
    meta = {}
    rules_root = os.path.join(_repo_root, 'rules')
    if not os.path.isdir(rules_root):
        return meta

    for lan in os.listdir(rules_root):
        lan_path = os.path.join(rules_root, lan)
        if not os.path.isdir(lan_path):
            continue
        if lan in ('tamper', 'test'):
            continue
        for fn in os.listdir(lan_path):
            if not (fn.startswith('CVI_') and fn.endswith('.py')):
                continue
            mod_name = 'rules.{lan}.{name}'.format(lan=lan, name=fn[:-3])
            try:
                mod = importlib.import_module(mod_name)
                cls = getattr(mod, fn[:-3])
                inst = cls()
                svid = str(getattr(inst, 'svid', '')).strip()
                if not svid:
                    continue
                meta[svid] = {
                    'rule_name': getattr(inst, 'vulnerability', '') or getattr(inst, 'rule_name', '') or fn[:-3],
                    'level': int(getattr(inst, 'level', 1)),
                    'language': getattr(inst, 'language', lan),
                }
            except Exception:
                continue
    return meta


def _iter_rule_files():
    rules_root = os.path.join(_repo_root, 'rules')
    if not os.path.isdir(rules_root):
        return
    for root, _dirs, files in os.walk(rules_root):
        for fn in files:
            if fn.startswith('CVI_') and fn.endswith('.py'):
                yield os.path.join(root, fn)


def _ensure_rules_present():
    for _ in _iter_rule_files():
        return
    raise RuntimeError('no rules found under rules/**/CVI_*.py')


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', default='.', help='scan target path')
    parser.add_argument('--output', default='artifacts/kunlun-ci.json', help='output report file')
    parser.add_argument('--fail-on', default=os.environ.get('KUNLUN_FAIL_ON', 'none'), help='none|low|medium|high|critical')
    parser.add_argument('--include-unconfirm', action='store_true', default=_coerce_bool(os.environ.get('KUNLUN_INCLUDE_UNCONFIRM', '0')))
    parser.add_argument('--with-vendor', action='store_true', default=_coerce_bool(os.environ.get('KUNLUN_WITH_VENDOR', '0')))
    parser.add_argument('--without-vendor', action='store_true', default=False)
    parser.add_argument('--rule', dest='special_rules', default=None)
    parser.add_argument('--language', default=None)
    parser.add_argument('--blackpath', dest='black_path', default=None)
    parser.add_argument('--tamper', dest='tamper_name', default=None)
    parser.add_argument('--unprecom', action='store_true', default=False)
    parser.add_argument('--settings-module', default=os.environ.get('DJANGO_SETTINGS_MODULE', 'Kunlun_M.settings_ci'))
    args = parser.parse_args(argv)

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', args.settings_module)
    try:
        m = importlib.import_module(args.settings_module)
        sys.modules['Kunlun_M.settings'] = m
    except Exception:
        pass

    try:
        args.output = os.path.abspath(args.output)
        if not args.target or not str(args.target).strip():
            raise ValueError('target is empty')
        if not os.path.exists(args.target):
            raise FileNotFoundError('target not found: {t}'.format(t=args.target))
        _ensure_rules_present()

        import django
        django.setup()
        from django.core.management import call_command

        call_command('migrate', interactive=False, verbosity=0, run_syncdb=True)

        import Kunlun_M.settings as settings
        settings.WITH_VENDOR = bool(args.with_vendor) and (not args.without_vendor)

        from django.utils import timezone
        from web.index.models import ScanTask, Rules, VendorVulns, get_and_check_scantask_project_id, get_and_check_scanresult
        from core import cli as core_cli
        from Kunlun_M.const import VUL_LEVEL, VENDOR_VUL_LEVEL

        target = args.target
        started_at = time.time()
        rule_meta = _load_rule_meta()

        task_name = 'ci_' + str(int(started_at)) + '_' + str(os.getpid())
        parameter_config = {
            'argv': sys.argv,
            'fail_on': args.fail_on,
            'include_unconfirm': bool(args.include_unconfirm),
            'with_vendor': bool(settings.WITH_VENDOR),
        }
        s = ScanTask(task_name=task_name, target_path=target, parameter_config=json.dumps(parameter_config, ensure_ascii=False))
        s.last_scan_time = timezone.now()
        s.is_finished = 2
        s.started_at = timezone.now()
        s.finished_at = None
        s.exit_code = None
        s.error_message = None
        s.save()

        from core.engine import Running
        Running(str(s.id)).status({'status': 'running', 'report': ''})

        try:
            core_cli.start(
                target,
                'json',
                '',
                args.special_rules,
                str(s.id),
                args.language,
                args.tamper_name,
                args.black_path,
                bool(args.include_unconfirm),
                bool(args.unprecom),
            )
        except Exception as e:
            s.is_finished = 0
            s.finished_at = timezone.now()
            s.exit_code = 1
            s.error_message = str(e)[:2000]
            s.save()
            raise

        s.is_finished = 1
        s.finished_at = timezone.now()
        s.exit_code = 0
        s.save()

        project_id = get_and_check_scantask_project_id(s.id)
        qs = get_and_check_scanresult(s.id).objects.filter(scan_project_id=project_id, is_active=True)
        if not args.include_unconfirm:
            qs = qs.filter(is_unconfirm=False)
        results = list(qs)

        vul_list = []
        counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        max_sev = 'none'
        max_rank = 0

        for sr in results:
            sev = 'low'
            rule_name = 'Unknown Rule'

            if str(sr.cvi_id) == '9999':
                try:
                    vendor_vuls_id = int(str(sr.vulfile_path).split(':')[-1])
                except Exception:
                    vendor_vuls_id = None
                if vendor_vuls_id:
                    vv = VendorVulns.objects.filter(id=vendor_vuls_id).first()
                else:
                    vv = None
                if vv:
                    rule_name = vv.title
                    sev = VENDOR_VUL_LEVEL[int(vv.severity)]
                else:
                    rule_name = 'SCA Scan'
                    sev = VENDOR_VUL_LEVEL[1]
            else:
                rm = rule_meta.get(str(sr.cvi_id))
                if rm:
                    rule_name = rm.get('rule_name') or rule_name
                    sev = VUL_LEVEL[int(rm.get('level', 1))]
                else:
                    rule = Rules.objects.filter(svid=sr.cvi_id).first()
                    if rule:
                        rule_name = rule.rule_name
                        sev = VUL_LEVEL[int(rule.level)]
                    else:
                        sev = VUL_LEVEL[1]

            rnk = _severity_rank(sev)
            if rnk > max_rank:
                max_rank = rnk
                max_sev = sev
            if sev in counts:
                counts[sev] += 1

            vul_list.append({
                'id': sr.id,
                'cvi_id': sr.cvi_id,
                'rule_name': rule_name,
                'severity': sev,
                'language': sr.language,
                'file': sr.vulfile_path,
                'is_unconfirm': bool(sr.is_unconfirm),
                'result_type': sr.result_type,
                'source_code': sr.source_code,
            })

        fail_rank = _severity_rank(args.fail_on)
        exit_code = 0
        reason = 'ok'
        if max_rank >= fail_rank and fail_rank > 0 and len(vul_list) > 0:
            exit_code = 2
            reason = 'threshold_reached'

        report = {
            'meta': {
                'target': target,
                'task_id': s.id,
                'project_id': project_id,
                'started_at': s.started_at.isoformat() if s.started_at else None,
                'finished_at': s.finished_at.isoformat() if s.finished_at else None,
                'fail_on': args.fail_on,
                'include_unconfirm': bool(args.include_unconfirm),
                'with_vendor': bool(settings.WITH_VENDOR),
                'settings_module': args.settings_module,
            },
            'summary': {
                'total': len(vul_list),
                'by_severity': counts,
                'max_severity': max_sev,
            },
            'vulnerabilities': vul_list,
            'exit': {
                'code': exit_code,
                'reason': reason,
            }
        }

        out = args.output
        _safe_makedirs(os.path.dirname(out))
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        return exit_code
    except SystemExit:
        raise
    except Exception:
        out = args.output if 'args' in locals() else 'artifacts/kunlun-ci.json'
        _safe_makedirs(os.path.dirname(out))
        err = {
            'exit': {
                'code': 1,
                'reason': 'exception',
            },
            'error': traceback.format_exc(),
        }
        try:
            with open(out, 'w', encoding='utf-8') as f:
                json.dump(err, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
