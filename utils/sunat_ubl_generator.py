"""
Generador de Comprobantes UBL 2.1 para SUNAT
Crea archivos XML según estándar UBL 2.1 de facturación electrónica
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
import uuid

class SUNATUBLGenerator:
    """Genera archivos XML en formato UBL 2.1 para comprobantes electrónicos"""
    
    # Namespaces UBL 2.1
    NAMESPACES = {
        'cac': 'urn:oasis:names:specification:ubl:schema:common:AggregateComponents-2',
        'cbc': 'urn:oasis:names:specification:ubl:schema:common:BasicComponents-2',
        'ext': 'urn:oasis:names:specification:ubl:schema:common:ExtensionComponents-2',
        'ds': 'http://www.w3.org/2000/09/xmldsig#',
        'ublext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2',
    }

    def __init__(self):
        """Inicializa el generador UBL"""
        self.ns = self.NAMESPACES

    def _create_element(self, tag: str, text: str = "", namespace: str = 'cbc') -> ET.Element:
        """Crea un elemento XML con namespace"""
        ns_prefix = self.ns.get(namespace, '')
        if ns_prefix:
            elem = ET.Element(f"{{{ns_prefix}}}{tag}")
        else:
            elem = ET.Element(tag)
        if text:
            elem.text = str(text)
        return elem

    def generar_invoice_xml(self, boleta_data: Dict) -> str:
        """
        Genera XML de Factura (Invoice) UBL 2.1
        
        Args:
            boleta_data: Dict con datos de la boleta
                - ruc: RUC del emisor
                - razon_social: Razón social
                - numero_serie: Serie (P, F, etc)
                - numero_correlativo: Número correlativo
                - tipo_cliente: RUC o DNI del cliente
                - cliente_nombre: Nombre del cliente
                - fecha_emision: Fecha emisión
                - fecha_vencimiento: Fecha vencimiento
                - items: Lista de items
                - subtotal: Subtotal (antes de impuestos)
                - igv: IGV (18%)
                - total: Total
                - moneda: Moneda (PEN, USD, etc)
                - direccion_emisor: Dirección del emisor
        
        Returns:
            String con XML formateado
        """
        
        # Crear raíz Invoice
        invoice = ET.Element(
            'Invoice',
            xmlns='urn:oasis:names:specification:ubl:schema:xsd:Invoice-2',
            **{f'xmlns:{k}': v for k, v in self.ns.items()}
        )

        # Versión y ID
        self._add_element(invoice, 'cbc', 'UBLVersionID', '2.1')
        self._add_element(invoice, 'cbc', 'CustomizationID', '2.0')
        
        # ID del comprobante (unique identifier)
        numero_serie = str(boleta_data.get('numero_serie', 'B') or 'B')
        numero_correlativo = str(boleta_data.get('numero_correlativo', '000001') or '000001')
        numero_completo = f"{numero_serie}{numero_correlativo.zfill(8)}"
        self._add_element(invoice, 'cbc', 'ID', numero_completo)
        
        # Tipo de documento (01 = Factura, 03 = Boleta)
        invoice_type = boleta_data.get('InvoiceTypeCode', '01')
        self._add_element(invoice, 'cbc', 'IssueDate', boleta_data.get('fecha_emision', ''))
        self._add_element(invoice, 'cbc', 'IssueTime', '00:00:00')
        self._add_element(invoice, 'cbc', 'DueDate', boleta_data.get('fecha_vencimiento', ''))
        self._add_element(invoice, 'cbc', 'InvoiceTypeCode', invoice_type)
        
        # Descripción
        self._add_element(invoice, 'cbc', 'DocumentCurrencyCode', boleta_data.get('moneda', 'PEN'))
        
        # FIRMA DIGITAL (Contenedor UBL 2.1 estándar)
        extensions = self._add_element(invoice, 'ext', 'UBLExtensions', '')
        extension = ET.SubElement(extensions, f"{{{self.ns['ext']}}}UBLExtension")
        content = ET.SubElement(extension, f"{{{self.ns['ext']}}}ExtensionContent")
        # El firmador buscará ExtensionContent para insertar la firma
        
        # Información del Emisor (Supplier)
        supplier = self._create_supplier(invoice, boleta_data)
        
        # Información del Cliente (Customer)
        customer = self._create_customer(invoice, boleta_data)
        
        # Impuestos Totales (IGV obligatorio)
        self._add_tax_total(invoice, boleta_data)
        
        # Líneas de detalle
        self._add_invoice_lines(invoice, boleta_data.get('items', []))
        
        # Totales
        self._add_legal_monetary_total(invoice, boleta_data)
        
        # Retorno XML formateado
        return self._pretty_print_xml(invoice)

    def _add_tax_total(self, parent: ET.Element, boleta_data: Dict) -> None:
        """Añade la sección TaxTotal (IGV 18%)"""
        tax_total = ET.SubElement(parent, f"{{{self.ns['cac']}}}TaxTotal")
        
        # Monto total del impuesto
        igv_monto = Decimal(str(boleta_data.get('igv', 0))).quantize(Decimal('0.01'))
        ET.SubElement(
            tax_total, 
            f"{{{self.ns['cbc']}}}TaxAmount", 
            currencyID=boleta_data.get('moneda', 'PEN')
        ).text = str(igv_monto)
        
        # Subtotal del impuesto (TaxSubtotal)
        tax_subtotal = ET.SubElement(tax_total, f"{{{self.ns['cac']}}}TaxSubtotal")
        
        # Base imponible
        subtotal = Decimal(str(boleta_data.get('subtotal', 0))).quantize(Decimal('0.01'))
        ET.SubElement(
            tax_subtotal, 
            f"{{{self.ns['cbc']}}}TaxableAmount", 
            currencyID=boleta_data.get('moneda', 'PEN')
        ).text = str(subtotal)
        
        # Monto del impuesto repetido en subtotal
        ET.SubElement(
            tax_subtotal, 
            f"{{{self.ns['cbc']}}}TaxAmount", 
            currencyID=boleta_data.get('moneda', 'PEN')
        ).text = str(igv_monto)
        
        # Categoría de impuesto (IGV = 1000)
        tax_category = ET.SubElement(tax_subtotal, f"{{{self.ns['cac']}}}TaxCategory")
        
        # Porcentaje del IGV (18.00)
        ET.SubElement(tax_category, f"{{{self.ns['cbc']}}}Percent").text = "18.00"
        
        # Tipo de afectación (10 = Gravado - Operación Onerosa)
        # Esto es vital para SUNAT
        ET.SubElement(tax_category, f"{{{self.ns['cbc']}}}TaxExemptionReasonCode").text = "10"
        
        tax_scheme = ET.SubElement(tax_category, f"{{{self.ns['cac']}}}TaxScheme")
        ET.SubElement(tax_scheme, f"{{{self.ns['cbc']}}}ID").text = "1000"
        ET.SubElement(tax_scheme, f"{{{self.ns['cbc']}}}Name").text = "IGV"
        ET.SubElement(tax_scheme, f"{{{self.ns['cbc']}}}TaxTypeCode").text = "VAT"

    def _create_supplier(self, parent: ET.Element, boleta_data: Dict) -> ET.Element:
        """Crea información del Emisor (Supplier/AccountingSupplierParty)"""
        supplier = ET.SubElement(
            parent,
            f"{{{self.ns['cac']}}}AccountingSupplierParty"
        )
        
        # Party
        party = ET.SubElement(supplier, f"{{{self.ns['cac']}}}Party")
        
        # Nombre comercial (opcional)
        ET.SubElement(
            party,
            f"{{{self.ns['cbc']}}}WebsiteURI"
        ).text = ""
        
        # RUC del emisor
        party_id = ET.SubElement(
            party,
            f"{{{self.ns['cac']}}}PartyIdentification"
        )
        ET.SubElement(
            party_id,
            f"{{{self.ns['cbc']}}}ID",
            schemeID="6"
        ).text = boleta_data.get('ruc', '')
        
        # Razón social
        legal_name = ET.SubElement(
            party,
            f"{{{self.ns['cac']}}}PartyLegalEntity"
        )
        ET.SubElement(
            legal_name,
            f"{{{self.ns['cbc']}}}RegistrationName"
        ).text = boleta_data.get('razon_social', '')
        
        # Dirección del emisor
        address = ET.SubElement(legal_name, f"{{{self.ns['cac']}}}RegistrationAddress")
        ET.SubElement(
            address,
            f"{{{self.ns['cbc']}}}CityName"
        ).text = "Lima"
        ET.SubElement(
            address,
            f"{{{self.ns['cbc']}}}CountrySubentity"
        ).text = "LIMA"
        
        country = ET.SubElement(address, f"{{{self.ns['cac']}}}Country")
        ET.SubElement(
            country,
            f"{{{self.ns['cbc']}}}IdentificationCode"
        ).text = "PE"
        
        return supplier

    def _create_customer(self, parent: ET.Element, boleta_data: Dict) -> ET.Element:
        """Crea información del Cliente (Customer/AccountingCustomerParty)"""
        customer = ET.SubElement(
            parent,
            f"{{{self.ns['cac']}}}AccountingCustomerParty"
        )
        
        party = ET.SubElement(customer, f"{{{self.ns['cac']}}}Party")
        
        # Tipo de identificación (1=DNI, 6=RUC)
        tipo_cliente = boleta_data.get('tipo_cliente', '1')
        party_id = ET.SubElement(party, f"{{{self.ns['cac']}}}PartyIdentification")
        ET.SubElement(
            party_id,
            f"{{{self.ns['cbc']}}}ID",
            schemeID=tipo_cliente
        ).text = boleta_data.get('numero_cliente', '')
        
        # Nombre del cliente
        legal_name = ET.SubElement(party, f"{{{self.ns['cac']}}}PartyLegalEntity")
        ET.SubElement(
            legal_name,
            f"{{{self.ns['cbc']}}}RegistrationName"
        ).text = boleta_data.get('cliente_nombre', '')
        
        return customer

    def _add_invoice_lines(self, parent: ET.Element, items: List[Dict]) -> None:
        """Añade líneas de detalle de la factura"""
        for idx, item in enumerate(items, 1):
            line = ET.SubElement(
                parent,
                f"{{{self.ns['cac']}}}InvoiceLine"
            )
            
            # Número de línea
            ET.SubElement(line, f"{{{self.ns['cbc']}}}ID").text = str(idx)
            
            # Cantidad
            cantidad = Decimal(str(item.get('cantidad', 1)))
            invoiced = ET.SubElement(line, f"{{{self.ns['cac']}}}InvoicedQuantity")
            invoiced.text = str(cantidad)
            invoiced.set('unitCode', item.get('unidad', 'C62'))  # C62 = unidad
            
            # Línea total
            ET.SubElement(
                line,
                f"{{{self.ns['cbc']}}}LineExtensionAmount"
            ).text = str(Decimal(str(item.get('total', 0))).quantize(Decimal('0.01')))
            
            # Descripción del item
            description = ET.SubElement(
                line,
                f"{{{self.ns['cac']}}}Item"
            )
            ET.SubElement(
                description,
                f"{{{self.ns['cbc']}}}Description"
            ).text = item.get('descripcion', '')
            
            # --- NUEVO: Impuestos por Línea (Obligatorio SUNAT) ---
            line_tax_total = ET.SubElement(line, f"{{{self.ns['cac']}}}TaxTotal")
            
            # Calcular IGV de la línea (18% del total de la línea si es gravado)
            line_total = Decimal(str(item.get('total', 0)))
            # Asumiendo que el total de la línea ya incluye IGV o se calcula aquí
            # Para propósitos de este generador, calcularemos el IGV a partir del total
            line_igv = (line_total * Decimal('0.18') / Decimal('1.18')).quantize(Decimal('0.01'))
            line_subtotal = (line_total - line_igv).quantize(Decimal('0.01'))
            
            ET.SubElement(
                line_tax_total,
                f"{{{self.ns['cbc']}}}TaxAmount",
                currencyID=boleta_data.get('moneda', 'PEN')
            ).text = str(line_igv)
            
            line_tax_subtotal = ET.SubElement(line_tax_total, f"{{{self.ns['cac']}}}TaxSubtotal")
            ET.SubElement(
                line_tax_subtotal,
                f"{{{self.ns['cbc']}}}TaxableAmount",
                currencyID=boleta_data.get('moneda', 'PEN')
            ).text = str(line_subtotal)
            
            ET.SubElement(
                line_tax_subtotal,
                f"{{{self.ns['cbc']}}}TaxAmount",
                currencyID=boleta_data.get('moneda', 'PEN')
            ).text = str(line_igv)
            
            line_tax_category = ET.SubElement(line_tax_subtotal, f"{{{self.ns['cac']}}}TaxCategory")
            ET.SubElement(line_tax_category, f"{{{self.ns['cbc']}}}Percent").text = "18.00"
            ET.SubElement(line_tax_category, f"{{{self.ns['cbc']}}}TaxExemptionReasonCode").text = "10"
            
            line_tax_scheme = ET.SubElement(line_tax_category, f"{{{self.ns['cac']}}}TaxScheme")
            ET.SubElement(line_tax_scheme, f"{{{self.ns['cbc']}}}ID").text = "1000"
            ET.SubElement(line_tax_scheme, f"{{{self.ns['cbc']}}}Name").text = "IGV"
            ET.SubElement(line_tax_scheme, f"{{{self.ns['cbc']}}}TaxTypeCode").text = "VAT"
            
            # Precio
            price_elem = ET.SubElement(line, f"{{{self.ns['cac']}}}Price")
            ET.SubElement(
                price_elem,
                f"{{{self.ns['cbc']}}}PriceAmount"
            ).text = str(Decimal(str(item.get('precio_unitario', 0))).quantize(Decimal('0.01')))

    def _add_legal_monetary_total(self, parent: ET.Element, boleta_data: Dict) -> None:
        """Añade totales monetarios"""
        totals = ET.SubElement(parent, f"{{{self.ns['cac']}}}LegalMonetaryTotal")
        
        # Línea total (antes de impuestos)
        ET.SubElement(
            totals,
            f"{{{self.ns['cbc']}}}LineExtensionAmount"
        ).text = str(Decimal(str(boleta_data.get('subtotal', 0))).quantize(Decimal('0.01')))
        
        # Subtotal
        ET.SubElement(
            totals,
            f"{{{self.ns['cbc']}}}TaxExclusiveAmount"
        ).text = str(Decimal(str(boleta_data.get('subtotal', 0))).quantize(Decimal('0.01')))
        
        # Total con impuestos
        ET.SubElement(
            totals,
            f"{{{self.ns['cbc']}}}TaxInclusiveAmount"
        ).text = str(Decimal(str(boleta_data.get('total', 0))).quantize(Decimal('0.01')))
        
        # Monto a pagar
        ET.SubElement(
            totals,
            f"{{{self.ns['cbc']}}}PayableAmount"
        ).text = str(Decimal(str(boleta_data.get('total', 0))).quantize(Decimal('0.01')))

    def _add_element(self, parent: ET.Element, namespace: str, tag: str, text: str) -> ET.Element:
        """Helper para añadir elementos con namespace"""
        ns_uri = self.ns.get(namespace, '')
        elem = ET.SubElement(parent, f"{{{ns_uri}}}{tag}")
        elem.text = str(text) if text else ""
        return elem

    def _pretty_print_xml(self, elem: ET.Element) -> str:
        """Formatea XML para mejor legibilidad"""
        rough_string = ET.tostring(elem, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ", encoding='utf-8').decode('utf-8')

    def generar_boleta_xml(self, boleta_data: Dict) -> str:
        """
        Genera XML de Boleta (tipo 03)
        Es similar a factura pero con tipo de documento diferente
        """
        boleta_data['InvoiceTypeCode'] = '03'  # 03 = Boleta
        return self.generar_invoice_xml(boleta_data)


# Ejemplo de uso
if __name__ == "__main__":
    generator = SUNATUBLGenerator()
    
    test_data = {
        'ruc': '20131312955',
        'razon_social': 'OPTICA TEST S.A.C.',
        'numero_serie': 'B',
        'numero_correlativo': '000001',
        'tipo_cliente': '1',
        'numero_cliente': '12345678',
        'cliente_nombre': 'JUAN PEREZ RODRIGUEZ',
        'fecha_emision': datetime.now().strftime('%Y-%m-%d'),
        'fecha_vencimiento': datetime.now().strftime('%Y-%m-%d'),
        'moneda': 'PEN',
        'subtotal': 100.00,
        'igv': 18.00,
        'total': 118.00,
        'items': [
            {
                'descripcion': 'Lentes oftalmicos',
                'cantidad': 1,
                'precio_unitario': 100.00,
                'total': 100.00,
                'unidad': 'C62'
            }
        ]
    }
    
    xml = generator.generar_invoice_xml(test_data)
    print(xml)
