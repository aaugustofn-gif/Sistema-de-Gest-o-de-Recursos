import json
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")
# 'tojson' não vem habilitado por padrão no Jinja2 puro (é um recurso do Flask) —
# precisa ser registrado manualmente para uso em <script> nos templates.
templates.env.filters["tojson"] = lambda valor: json.dumps(valor)
