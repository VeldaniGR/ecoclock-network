# fragmento conceptual en client/cli.py (cmd_run o similar)
payload = task["payload"]   # ya parseado
if isinstance(payload, str):
    payload = json.loads(payload)

task_type = payload.get("type")

if task_type == "ndvi":
    from client.ndvi import compute
elif task_type == "posidonia":
    from client.posidonia import compute
elif task_type == "biodiversity":
    from client.biodiversity import compute
else:
    raise CLIError(f"Tipo de tarea desconocido: {task_type}")

output = compute(payload)
# ... submit normal
