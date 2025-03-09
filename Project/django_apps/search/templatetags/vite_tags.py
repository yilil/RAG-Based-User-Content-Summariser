import json
from django import template
from django.conf import settings
from pathlib import Path
 
register = template.Library()
 
@register.simple_tag
def vite_asset(file: str):
    """Resolve the Vite-built asset path from manifest.json."""
    manifest_path = Path(settings.BASE_DIR) / "Frontend/static/manifest.json"
    if not manifest_path.exists():
        raise RuntimeError(f"{manifest_path} not found. Did you run `npm run build`?")
    with open(manifest_path) as f:
        manifest = json.load(f)
     
    # 根据 manifest 返回文件路径
    return f"/static/{manifest[file]['file']}"