"""Conservative checks before running tests with a forced OpenBLAS kernel."""
import json
import os
import platform
import subprocess
import sys
import unittest
from pathlib import Path

# Linux reports AVX only when the OS enables the necessary register state.
REQUIRED_FLAGS = {
    'Haswell': {'avx', 'avx2', 'fma', 'bmi1', 'bmi2', 'f16c', 'xsave', 'ssse3', 'sse4_1', 'sse4_2'},
    'Sandybridge': {'avx', 'xsave', 'ssse3', 'sse4_1', 'sse4_2'},
}

def common_cpu_flags(cpuinfo):
    """Use the intersection, so scheduling on a different CPU remains safe."""
    processors=[]
    for block in cpuinfo.strip().split('\n\n'):
        fields=dict(line.split(':',1) for line in block.splitlines() if ':' in line)
        fields={key.strip():value.strip() for key,value in fields.items()}
        if 'processor' in fields:
            if not fields.get('flags'):return set()
            processors.append(set(fields['flags'].split()))
    return set.intersection(*processors) if processors else set()

def backend_reason(pools, requested=None):
    blas=[pool for pool in pools if pool.get('user_api')=='blas']
    # Multiple BLAS implementations cannot safely be attributed to NumPy.
    if len(blas)!=1 or blas[0].get('internal_api')!='openblas':
        return 'NumPy OpenBLAS backend cannot be identified unambiguously'
    if requested and str(blas[0].get('architecture') or '').lower()!=requested.lower():
        return 'OpenBLAS did not select the requested '+requested+' kernel'
    return None

def support_reason(core, system, machine, flags, pools):
    if system!='linux' or machine.lower() not in ('x86_64','amd64'):
        return 'OpenBLAS kernel check requires Linux x86-64'
    if core not in REQUIRED_FLAGS:return 'Unknown OpenBLAS kernel'
    missing=REQUIRED_FLAGS[core]-flags
    if missing:return 'CPU or OS lacks required features for '+core+': '+', '.join(sorted(missing))
    return backend_reason(pools)

def pool_info():
    from threadpoolctl import threadpool_info
    return threadpool_info()

def probe_reason(core):
    if not sys.platform.startswith('linux') or platform.machine().lower() not in ('x86_64','amd64'):
        return 'OpenBLAS kernel check requires Linux x86-64'
    try:
        flags=common_cpu_flags(Path('/proc/cpuinfo').read_text())
        pools=pool_info()
    except (ImportError, OSError, RuntimeError):
        return 'CPU capabilities or OpenBLAS backend cannot be inspected'
    return support_reason(core,'linux',platform.machine(),flags,pools)

def skip_or_fail(reason):
    if os.environ.get('SPRITE_REQUIRE_OPENBLAS_CHECKS')=='1':
        raise AssertionError(reason)
    raise unittest.SkipTest(reason)

def run_with_kernel(core, script):
    """Probe before launching, then verify dispatch before any test rendering."""
    reason=probe_reason(core)
    if reason:skip_or_fail(reason)
    env=os.environ.copy();env['OPENBLAS_CORETYPE']=core
    env['PYTHONPATH']=os.pathsep.join(filter(None,[str(Path(__file__).resolve().parent),env.get('PYTHONPATH','')]))
    wrapper='''import json\nfrom blas_capabilities import backend_reason,pool_info\nbefore=pool_info()\nimport numpy\nreason=("BLAS was loaded before NumPy; its backend is ambiguous" if any(p.get("user_api")=="blas" for p in before) else backend_reason(pool_info(),%r))\nif reason:\n print(json.dumps({"skip":reason}))\nelse:\n exec(%r)\n print(json.dumps({"result":payload}))''' % (core,script)
    result=subprocess.run([sys.executable,'-c',wrapper],env=env,capture_output=True,text=True,check=True,timeout=60)
    output=json.loads(result.stdout)
    if 'skip' in output:skip_or_fail(output['skip'])
    return output['result']
