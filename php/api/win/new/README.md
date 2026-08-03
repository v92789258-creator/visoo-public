# Cloud Snapshot API (`/api/win/new`)

These endpoints store device data by folder:

- `viso-<usuario_madre>+<codigo_dispositivo>/clientes.json`
- `viso-<usuario_madre>+<codigo_dispositivo>/pacientes.json`
- `viso-<usuario_madre>+<codigo_dispositivo>/productos.json`
- `viso-<usuario_madre>+<codigo_dispositivo>/meta.json`

## Endpoints

- `upload_device_snapshot.php`
- `download_device_snapshot.php`
- `list_device_snapshots.php`
- `sync_child_devices.php` (uses MySQL table `dispositivos_hijos`)

## Example upload (child device)

```bash
curl -X POST "https://api.yhana.cloud/win/new/upload_device_snapshot.php" \
  -H "Content-Type: application/json" \
  -d '{
    "usuario_madre":"alex9121",
    "codigo_dispositivo":"OPTICA-01",
    "snapshot":{
      "clientes":[{"dni":"123","nombre":"A"}],
      "pacientes":[{"dni":"456","nombre":"B"}],
      "productos":[{"codigo":"P1","nombre":"Lente X"}]
    },
    "device_info":{"nombre_optica":"Sucursal Centro","ciudad":"Lima"}
  }'
```

## Example list (main device)

```bash
curl "https://api.yhana.cloud/win/new/list_device_snapshots.php?usuario_madre=alex9121&include_meta=1"
```

## Example download one dataset (main device)

```bash
curl "https://api.yhana.cloud/win/new/download_device_snapshot.php?usuario_madre=alex9121&codigo_dispositivo=OPTICA-01&dataset=productos&include_data=1"
```
