import datetime
import traceback

from PyQt5.QtWidgets import QMessageBox

from utils.file_handler import cargar_kardex, cargar_productos, cargar_ventas, guardar_kardex, guardar_productos, guardar_ventas


def eliminar_venta(page, sale):
    """Elimina un registro de venta despues de confirmar."""
    try:
        venta_id = sale.get("id", "")
        venta_fecha = sale.get("fecha", "")
        venta_total = float(sale.get("total", 0) or 0)

        reply = QMessageBox.question(
            page,
            "Confirmar eliminacion",
            f"Estas seguro que desea eliminar esta venta?\n\n"
            f"ID: {venta_id}\n"
            f"Fecha: {venta_fecha}\n"
            f"Total: S/. {venta_total:.2f}\n\n"
            f"Esta accion NO se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.No:
            return

        ventas = cargar_ventas(page.username)
        if not ventas:
            QMessageBox.warning(page, "Error", "No se encontraron ventas para eliminar.")
            return

        ventas_eliminadas = []
        ventas_filtradas = []
        venta_id_str = str(venta_id).strip()
        if venta_id_str:
            for venta in ventas:
                if str(venta.get("id", "")).strip() == venta_id_str:
                    ventas_eliminadas.append(venta)
                else:
                    ventas_filtradas.append(venta)
        else:
            encontrada = False
            for venta in ventas:
                misma_fecha = venta.get("fecha", "") == venta_fecha
                mismo_dni = str(venta.get("paciente_dni", "")).strip() == str(sale.get("paciente_dni", "")).strip()
                try:
                    mismo_total = abs(float(venta.get("total", 0) or 0) - venta_total) < 0.01
                except (TypeError, ValueError):
                    mismo_total = False

                if (not encontrada) and misma_fecha and mismo_dni and mismo_total:
                    ventas_eliminadas.append(venta)
                    encontrada = True
                else:
                    ventas_filtradas.append(venta)

        if not ventas_eliminadas:
            QMessageBox.warning(page, "Error", "No se pudo encontrar la venta para eliminar.")
            return

        productos = cargar_productos(page.username)
        productos_por_nombre = {}
        for producto in productos:
            if not isinstance(producto, dict):
                continue
            nombre_producto = str(producto.get("nombre", "")).strip()
            if nombre_producto:
                productos_por_nombre[nombre_producto.lower()] = producto

        stock_restaurado = 0
        items_restaurados = 0
        productos_no_encontrados = []
        productos_creados = []
        productos_creados_keys = set()
        kardex_entradas = []

        def generar_codigo_producto():
            codigos_numericos = []
            for p in productos:
                if not isinstance(p, dict):
                    continue
                codigo_raw = str(p.get("codigo", "")).strip()
                if codigo_raw.isdigit():
                    codigos_numericos.append(int(codigo_raw))
            siguiente = (max(codigos_numericos) + 1) if codigos_numericos else 1
            return f"{siguiente:07d}"

        for venta_eliminada in ventas_eliminadas:
            for item in venta_eliminada.get("items", []):
                nombre_item = str(item.get("nombre") or item.get("producto") or "").strip()
                if not nombre_item:
                    continue
                nombre_key = nombre_item.lower()

                try:
                    cantidad = int(float(item.get("cantidad", 0) or 0))
                except (TypeError, ValueError):
                    cantidad = 0
                if cantidad <= 0:
                    continue

                if nombre_key in productos_creados_keys:
                    continue

                producto = productos_por_nombre.get(nombre_key)
                if not producto:
                    precio_ref = float(item.get("precio_unitario", 0) or 0)
                    crear = QMessageBox.question(
                        page,
                        "Producto inexistente",
                        f"El producto '{nombre_item}' no existe en inventario.\n\nDesea crear este producto con 1 de stock?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes,
                    )
                    if crear == QMessageBox.Yes:
                        nuevo_producto = {
                            "codigo": generar_codigo_producto(),
                            "nombre": nombre_item,
                            "marca": "",
                            "categoria": "General",
                            "material": "",
                            "colors": [],
                            "talla": "",
                            "tipo_lente": "",
                            "stock": 1,
                            "costo": precio_ref,
                            "venta": precio_ref,
                            "precio_regular": precio_ref,
                            "caracteristicas": {
                                "polarizado": False,
                                "uv": False,
                                "antireflejo": False,
                                "fotocromatico": False,
                                "blue_light": False,
                            },
                            "variantes": {
                                "material": False,
                                "colores": False,
                                "talla": False,
                                "tipo_lente": False,
                            },
                            "created_at": datetime.datetime.now().isoformat(),
                            "image_path": "",
                        }
                        productos.append(nuevo_producto)
                        productos_por_nombre[nombre_key] = nuevo_producto
                        productos_creados.append(nombre_item)
                        productos_creados_keys.add(nombre_key)
                        stock_restaurado += 1
                        items_restaurados += 1
                        kardex_entradas.append(
                            {
                                "producto": nombre_item,
                                "cantidad": 1,
                                "costo_unitario": precio_ref,
                                "stock_final": 1,
                            }
                        )
                    else:
                        if nombre_item not in productos_no_encontrados:
                            productos_no_encontrados.append(nombre_item)
                    continue

                try:
                    stock_actual = int(float(producto.get("stock", 0) or 0))
                except (TypeError, ValueError):
                    stock_actual = 0

                producto["stock"] = stock_actual + cantidad
                stock_restaurado += cantidad
                items_restaurados += 1
                costo_kardex = item.get("precio_unitario", producto.get("costo", 0))
                kardex_entradas.append(
                    {
                        "producto": producto.get("nombre", nombre_item),
                        "cantidad": cantidad,
                        "costo_unitario": costo_kardex,
                        "stock_final": producto.get("stock", 0),
                    }
                )

        from utils.trash_manager import move_to_trash

        for venta_eliminada in ventas_eliminadas:
            move_to_trash(
                page.username,
                "ventas",
                venta_eliminada,
                source="sales_page.delete",
                extra={"stock_adjusted_on_delete": True},
            )

        guardar_ventas(page.username, ventas_filtradas)
        if productos:
            guardar_productos(page.username, productos)

        try:
            kardex_data = cargar_kardex(page.username)
            fecha_kardex = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            for entry in kardex_entradas:
                costo_unitario = float(entry.get("costo_unitario", 0) or 0)
                cantidad = int(float(entry.get("cantidad", 0) or 0))
                kardex_data.append(
                    {
                        "fecha": fecha_kardex,
                        "movimiento": "Entrada - Anulacion de venta",
                        "producto": entry.get("producto", ""),
                        "cantidad": cantidad,
                        "costo_unitario": costo_unitario,
                        "valor_total": costo_unitario * cantidad,
                        "stock_final": entry.get("stock_final", 0),
                    }
                )
            guardar_kardex(page.username, kardex_data)
        except Exception:
            pass

        page._reload_sales()

        mensaje = (
            f"Venta eliminada correctamente.\n\n"
            f"ID: {venta_id}\n"
            f"Monto: S/. {venta_total:.2f}\n"
            f"Stock restaurado: {stock_restaurado} unidad(es) en {items_restaurados} item(s)."
        )
        if productos_no_encontrados:
            mensaje += "\n\nAdvertencia: no se encontraron en inventario estos producto(s):\n" + ", ".join(productos_no_encontrados)
        if productos_creados:
            mensaje += "\n\nProducto(s) creado(s) con stock inicial 1:\n" + ", ".join(productos_creados)
        QMessageBox.information(page, "Exito", mensaje)
    except Exception as e:
        traceback.print_exc()
        QMessageBox.critical(page, "Error", f"Error al eliminar la venta:\n{str(e)}")
