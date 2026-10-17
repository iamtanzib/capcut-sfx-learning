"""Download and verify the local speech models; normal inference is offline."""
import os
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING']='1'
os.environ.setdefault('CT2_FORCE_CPU_ISA','GENERIC')
os.environ.setdefault('CT2_USE_MKL','0')
from faster_whisper import WhisperModel
import ctranslate2
import soundpilot as s

print('CPU compute types:',sorted(ctranslate2.get_supported_compute_types('cpu')),flush=True)
for name in ('tiny.en','base.en'):
    model=WhisperModel(name,device='cpu',compute_type='int8',cpu_threads=2,num_workers=1,
        download_root=str(s.BASE/'models'/'speech'))
    print('READY',name,flush=True)
